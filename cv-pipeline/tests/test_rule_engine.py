"""Rule engine unit tests — geometric helpers and per-rule logic.

These tests exercise the geometric predicates (IoU, containment, vector angle)
plus each individual violation rule against synthetic pipeline data dicts.
They do NOT require a database or GPU — pure unit tests.
"""

import math

import pytest

# Import via module path so the package is on sys.path via pyproject.toml
from app.pipeline.rule_engine import (
    _iou,
    _is_inside,
    _top_fraction,
    _vector_angle,
    evaluate,
    _rule_helmet,
    _rule_triple_riding,
    _rule_wrong_side,
    _rule_stop_line,
    _rule_overloading,
)


# ── Geometric helpers ─────────────────────────────────────────────────────────

class TestIoU:
    def test_no_overlap(self):
        # Two side-by-side boxes
        assert _iou([0, 0, 10, 10], [20, 0, 30, 10]) == 0.0

    def test_full_overlap(self):
        # Same box
        assert _iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0

    def test_partial_overlap(self):
        # 50% overlap each (intersection = 50)
        a = [0, 0, 10, 10]  # area 100
        b = [5, 0, 15, 10]  # area 100, intersection 50
        assert 0.4 < _iou(a, b) < 0.6

    def test_contained_box(self):
        # b fully inside a
        a = [0, 0, 100, 100]
        b = [25, 25, 75, 75]
        iou = _iou(a, b)
        assert 0.5 < iou < 0.75  # >50% by area ratio

    def test_degenerate_zero_area(self):
        assert _iou([0, 0, 0, 10], [0, 0, 10, 10]) == 0.0


class TestIsInside:
    def test_contained(self):
        assert _is_inside([20, 20, 80, 80], [0, 0, 100, 100], threshold=0.7)

    def test_partially_outside(self):
        # Inner box mostly outside outer
        assert not _is_inside([80, 80, 120, 120], [0, 0, 100, 100], threshold=0.5)

    def test_threshold_70_percent(self):
        # 70% containment threshold
        inner = [0, 0, 10, 10]  # area 100
        outer = [0, 0, 10, 11]  # overlap = 100, inner area = 100, ratio=1.0
        assert _is_inside(inner, outer, threshold=0.7)

    def test_below_threshold(self):
        inner = [45, 0, 55, 10]  # barely inside
        outer = [0, 0, 100, 10]
        assert not _is_inside(inner, outer, threshold=0.9)


class TestTopFraction:
    def test_20_percent_of_height(self):
        result = _top_fraction([0, 0, 100, 200], fraction=0.2)
        assert result == [0, 0, 100, 40]  # top 20% of y

    def test_default_20_percent(self):
        result = _top_fraction([0, 0, 100, 200])
        assert result == [0, 0, 100, 40]

    def test_fraction_10_percent(self):
        result = _top_fraction([0, 0, 50, 100], fraction=0.1)
        assert result == [0, 0, 50, 10]


class TestVectorAngle:
    def test_east(self):
        assert abs(_vector_angle([1, 0]) - 0) < 1e-6

    def test_south(self):
        assert abs(_vector_angle([0, 1]) - 90) < 1e-6

    def test_west(self):
        assert abs(_vector_angle([-1, 0]) - 180) < 1e-6

    def test_north(self):
        assert abs(_vector_angle([0, -1]) - 270) < 1e-6

    def test_wraps_360(self):
        assert _vector_angle([1, 0.0001]) < 1  # near 0 degrees


# ── Rule 1: Helmet ─────────────────────────────────────────────────────────────

def _make_pipeline(stage2: dict, stage3: dict) -> dict:
    return {
        "stage_2_detection": stage2,
        "stage_3_secondary": stage3,
    }


def test_helmet_no_helmet_in_head_region():
    """A rider with a no_helmet bbox in the head region should trigger."""
    pipeline = _make_pipeline(
        stage2={
            "detections": [
                {"class": "motorcycle", "bbox": [0, 0, 100, 100]},
            ]
        },
        stage3={
            "secondary_detections": [
                {
                    "motorcycle_bbox": [0, 0, 100, 100],
                    "detections": [
                        # Rider covering the full bike
                        {"class": "rider", "bbox": [10, 0, 90, 90], "confidence": 0.9},
                        # Head region would be [10, 0, 90, 18]
                        # Helmet detection in head region
                        {"class": "no_helmet", "bbox": [40, 2, 60, 16], "confidence": 0.85},
                    ],
                }
            ]
        },
    )
    results = _rule_helmet(pipeline)
    assert len(results) >= 1
    assert any(v.violation_type == "helmet" for v in results)


def test_helmet_with_helmet_no_violation():
    """A rider with a helmet in the head region should NOT trigger."""
    pipeline = _make_pipeline(
        stage2={
            "detections": [
                {"class": "motorcycle", "bbox": [0, 0, 100, 100]},
            ]
        },
        stage3={
            "secondary_detections": [
                {
                    "motorcycle_bbox": [0, 0, 100, 100],
                    "detections": [
                        {"class": "rider", "bbox": [10, 0, 90, 90], "confidence": 0.9},
                        # Helmet in head region — compliant
                        {"class": "helmet", "bbox": [40, 2, 60, 16], "confidence": 0.9},
                    ],
                }
            ]
        },
    )
    # Should not fire because helmet is present in head region
    results = _rule_helmet(pipeline)
    # All detections have helmets → no violation
    assert all(v.violation_type != "helmet" for v in results)


def test_helmet_no_motorcycles():
    """When there are no motorcycles, helmet rule returns empty."""
    results = _rule_helmet(_make_pipeline({"detections": []}, {"secondary_detections": []}))
    assert results == []


# ── Rule 2: Triple Riding ───────────────────────────────────────────────────────

def test_triple_riding_three_riders():
    """Three riders on one motorcycle → violation."""
    pipeline = {
        "stage_3_secondary": {
            "secondary_detections": [
                {
                    "motorcycle_bbox": [10, 10, 200, 200],
                    "detections": [
                        {"class": "rider", "bbox": [50, 10, 100, 200], "confidence": 0.9},
                        {"class": "rider", "bbox": [80, 10, 130, 200], "confidence": 0.9},
                        {"class": "rider", "bbox": [110, 10, 160, 200], "confidence": 0.9},
                    ],
                }
            ]
        }
    }
    results = _rule_triple_riding(pipeline)
    assert len(results) == 1
    assert results[0].violation_type == "triple_riding"


def test_triple_riding_two_riders():
    """Two riders → no violation."""
    pipeline = {
        "stage_3_secondary": {
            "secondary_detections": [
                {
                    "motorcycle_bbox": [10, 10, 200, 200],
                    "detections": [
                        {"class": "rider", "bbox": [50, 10, 100, 200], "confidence": 0.9},
                        {"class": "rider", "bbox": [80, 10, 130, 200], "confidence": 0.9},
                    ],
                }
            ]
        }
    }
    results = _rule_triple_riding(pipeline)
    assert results == []


# ── Rule 3: Wrong Side ─────────────────────────────────────────────────────────

def test_wrong_side_vehicles_flowing_against_legal():
    """Trajectory 180° opposite to legal flow vector → violation."""
    # Legal flow = south (0, 1).  Vehicle goes north (dx=0, dy=-1)
    pipeline = {
        "stage_4_tracking": {
            "tracks": [
                {
                    "track_id": 1,
                    "class": "car",
                    "trajectory": [[100, 200], [100, 100]],  # going north
                    "speed_kmph": 45.0,
                    "direction": "north",
                }
            ]
        },
        "camera_config": {
            "legal_flow_vector": [0, 1],  # south
        },
    }
    results = _rule_wrong_side(pipeline)
    assert len(results) == 1
    assert results[0].violation_type == "wrong_side_driving"
    assert results[0].track_id == 1


def test_wrong_side_within_120_degrees():
    """Trajectory within ±120° of legal → no violation."""
    pipeline = {
        "stage_4_tracking": {
            "tracks": [
                {
                    "track_id": 1,
                    "class": "car",
                    "trajectory": [[100, 100], [120, 200]],  # going roughly south
                    "speed_kmph": 45.0,
                    "direction": "south",
                }
            ]
        },
        "camera_config": {"legal_flow_vector": [0, 1]},
    }
    results = _rule_wrong_side(pipeline)
    assert results == []


# ── Rule 4: Stop Line ───────────────────────────────────────────────────────────

def test_stop_line_red_light_vehicle_crossing():
    """RED light + vehicle crossing stop line polygon → violation."""
    pipeline = {
        "camera_config": {
            "stop_line_polygon": [[0, 100], [200, 100], [200, 105], [0, 105]],
            "traffic_light_state": "green",  # default; overridden below
        },
        "stage_2_detection": {
            "detections": [
                {
                    "class": "traffic_light",
                    "bbox": [100, 50, 110, 60],
                    # state not provided by stage 2 in this test → fallback to camera_config
                }
            ]
        },
        "stage_4_tracking": {
            "tracks": [
                {
                    "track_id": 5,
                    "class": "car",
                    "trajectory": [[100, 120]],  # inside stop line polygon
                    "speed_kmph": 30.0,
                }
            ]
        },
    }
    # Override light to RED in the camera_config to simulate model output
    pipeline["camera_config"]["traffic_light_state"] = "red"
    results = _rule_stop_line(pipeline)
    assert len(results) == 1
    assert results[0].violation_type == "stop_line"


def test_stop_line_green_light_no_violation():
    """GREEN light → no stop-line violation regardless of position."""
    pipeline = {
        "camera_config": {
            "stop_line_polygon": [[0, 100], [200, 100], [200, 105], [0, 105]],
            "traffic_light_state": "green",
        },
        "stage_2_detection": {"detections": []},
        "stage_4_tracking": {
            "tracks": [
                {"track_id": 5, "class": "car", "trajectory": [[100, 102]]}
            ]
        },
    }
    results = _rule_stop_line(pipeline)
    assert results == []


def test_stop_line_no_polygon_configured():
    """No stop_line_polygon in camera_config → skip rule cleanly."""
    pipeline = {
        "camera_config": {},
        "stage_2_detection": {},
        "stage_4_tracking": {"tracks": [{"track_id": 5, "trajectory": [[100, 102]]}]},
    }
    results = _rule_stop_line(pipeline)
    assert results == []


# ── Rule 5: Overloading ─────────────────────────────────────────────────────────

def test_overloading_goods_exceed_width_threshold():
    """Cargo >120% vehicle width → violation."""
    pipeline = {
        "stage_2_detection": {
            "detections": [
                {
                    "class": "truck",
                    "bbox": [0, 0, 200, 100],
                }
            ],
            "cargo_detections": [
                {
                    "class": "cargo",
                    "bbox": [-20, 20, 220, 80],  # wider than truck
                    "confidence": 0.8,
                }
            ],
        }
    }
    results = _rule_overloading(pipeline)
    assert len(results) == 1
    assert results[0].violation_type == "overloading"


def test_overloading_cargo_within_limits():
    """Cargo within 120% width / 150% height → no violation."""
    pipeline = {
        "stage_2_detection": {
            "detections": [
                {"class": "truck", "bbox": [100, 100, 300, 200]},
            ],
            "cargo_detections": [
                {
                    "class": "cargo",
                    "bbox": [95, 95, 305, 205],  # barely exceeds
                    "confidence": 0.7,
                }
            ],
        }
    }
    results = _rule_overloading(pipeline)
    assert results == []


def test_overloading_no_cargo_detections():
    """Without cargo_detections the rule returns empty."""
    pipeline = {
        "stage_2_detection": {
            "detections": [
                {"class": "truck", "bbox": [0, 0, 200, 100]},
            ]
        }
    }
    assert _rule_overloading(pipeline) == []


# ── Full evaluate() ──────────────────────────────────────────────────────────────

def test_evaluate_runs_all_rules():
    """evaluate() aggregates results from all 5 rules with correct output shape."""
    pipeline = {
        "stage_2_detection": {
            "detections": [
                {"class": "motorcycle", "bbox": [0, 0, 100, 100], "confidence": 0.9},
            ]
        },
        "stage_3_secondary": {
            "secondary_detections": [
                {
                    "motorcycle_bbox": [0, 0, 100, 100],
                    "detections": [
                        # Triple riding: 3 riders
                        {"class": "rider", "bbox": [10, 0, 90, 80], "confidence": 0.9},
                        {"class": "rider", "bbox": [25, 0, 70, 80], "confidence": 0.9},
                        {"class": "rider", "bbox": [40, 0, 60, 80], "confidence": 0.9},
                        # no_helmet for helmet rule
                        {"class": "no_helmet", "bbox": [40, 50, 55, 100], "confidence": 0.85},
                    ],
                }
            ]
        },
    }
    result = evaluate(pipeline)

    assert "violations_detected" in result
    assert "violation_types" in result
    assert isinstance(result["violations_detected"], list)
    assert isinstance(result["violation_types"], list)

    # Both helmet and triple_riding should appear
    assert "helmet" in result["violation_types"]
    assert "triple_riding" in result["violation_types"]


def test_evaluate_empty_pipeline():
    """Empty pipeline data → no violations, empty lists."""
    result = evaluate({})
    assert result["violations_detected"] == []
    assert result["violation_types"] == []