"""Deterministic rule engine for TrafficVision AI.

Evaluates computer-vision detections against the 5 violation types
defined in `VIOLATION_RULE_ENGINE.md`.

Phase 5 (Mock) runs these rules over the static mock pipeline data.
Phase 8 will swap the upstream stages for real models, but the rule
engine itself stays unchanged.
"""

import math
from dataclasses import dataclass, field
from typing import Any


# ── Geometric helpers ───────────────────────────────────────────────────

def _iou(b1: list[float], b2: list[float]) -> float:
    """Intersection-over-Union of two bboxes: [x1, y1, x2, y2]."""
    x1 = max(b1[0], b2[0])
    y1 = max(b1[1], b2[1])
    x2 = min(b1[2], b2[2])
    y2 = min(b1[3], b2[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    union = area1 + area2 - inter
    return inter / union if union > 0 else 0.0


def _is_inside(inner: list[float], outer: list[float], threshold: float = 0.7) -> bool:
    """Check if `inner` is mostly contained within `outer`."""
    x1 = max(inner[0], outer[0])
    y1 = max(inner[1], outer[1])
    x2 = min(inner[2], outer[2])
    y2 = min(inner[3], outer[3])
    if x2 <= x1 or y2 <= y1:
        return False
    inter = (x2 - x1) * (y2 - y1)
    inner_area = max(1, (inner[2] - inner[0]) * (inner[3] - inner[1]))
    return inter / inner_area >= threshold


def _top_fraction(bbox: list[float], fraction: float = 0.2) -> list[float]:
    """Return the top N%% (default 20%%) of a bbox."""
    x1, y1, x2, y2 = bbox
    height = y2 - y1
    return [x1, y1, x2, y1 + height * fraction]


def _vector_angle(v: list[float]) -> float:
    """Return the angle of a vector in degrees (0-360)."""
    return (math.degrees(math.atan2(v[1], v[0])) + 360) % 360


def _bbox_bottom_edge_y(bbox: list[float]) -> float:
    """Return the y-coordinate of the bottom edge of a bbox."""
    return bbox[3]


def _bbox_center(bbox: list[float]) -> tuple[float, float]:
    """Return (cx, cy) of a bbox."""
    return ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)


# ── Violation dataclass ─────────────────────────────────────────────────

@dataclass
class ViolationResult:
    track_id: int | None
    vehicle_class: str | None
    violation_type: str
    confidence: float
    plate_text: str | None = None
    plate_bbox: list[float] | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "track_id": self.track_id,
            "vehicle_class": self.vehicle_class,
            "violation_type": self.violation_type,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }
        if self.plate_text:
            d["plate_text"] = self.plate_text
        if self.plate_bbox:
            d["plate_bbox"] = self.plate_bbox
        return d


# ── Rule 1: Helmet ─────────────────────────────────────────────────────

def _rule_helmet(pipeline_data: dict) -> list[ViolationResult]:
    """Trigger if a motorcycle rider has no helmet or a `no_helmet` class."""
    violations: list[ViolationResult] = []

    stage2 = pipeline_data.get("stage_2_detection", {})
    stage3 = pipeline_data.get("stage_3_secondary", {})

    if not stage2 or not stage3:
        return violations

    moto_bboxes = {
        tuple(d["bbox"]): d for d in stage2.get("detections", [])
        if d.get("class") == "motorcycle"
    }
    secondary = stage3.get("secondary_detections", [])

    for group in secondary:
        moto_bbox = group.get("motorcycle_bbox")
        if not moto_bbox or tuple(moto_bbox) not in moto_bboxes:
            continue

        riders = [d for d in group.get("detections", []) if d.get("class") == "rider"]
        accessories = group.get("detections", [])

        for rider in riders:
            rider_bbox = rider.get("bbox")
            if not rider_bbox:
                continue

            head_region = _top_fraction(rider_bbox, fraction=0.2)

            # Check if a `helmet` or `no_helmet` is in the head region
            helmet_in_head = any(
                a.get("class") == "helmet" and _is_inside(a["bbox"], head_region)
                for a in accessories
            )
            no_helmet_in_head = any(
                a.get("class") == "no_helmet" and _is_inside(a["bbox"], head_region)
                for a in accessories
            )

            if no_helmet_in_head or not helmet_in_head:
                violations.append(
                    ViolationResult(
                        track_id=None,
                        vehicle_class="motorcycle",
                        violation_type="helmet",
                        confidence=rider.get("confidence", 0.8),
                        evidence={
                            "rider_bbox": rider_bbox,
                            "head_region": head_region,
                            "no_helmet_found": no_helmet_in_head,
                            "helmet_found": helmet_in_head,
                        },
                    )
                )

    return violations


# ── Rule 2: Triple Riding ──────────────────────────────────────────────

def _rule_triple_riding(pipeline_data: dict) -> list[ViolationResult]:
    """Trigger if a two-wheeler carries 3 or more riders."""
    violations: list[ViolationResult] = []

    stage3 = pipeline_data.get("stage_3_secondary", {})
    if not stage3:
        return violations

    for group in stage3.get("secondary_detections", []):
        riders = [d for d in group.get("detections", []) if d.get("class") == "rider"]
        if len(riders) >= 3:
            violations.append(
                ViolationResult(
                    track_id=None,
                    vehicle_class="motorcycle",
                    violation_type="triple_riding",
                    confidence=min(r.get("confidence", 0.8) for r in riders),
                    evidence={
                        "rider_count": len(riders),
                        "motorcycle_bbox": group.get("motorcycle_bbox"),
                    },
                )
            )

    return violations


# ── Rule 3: Wrong Side Driving ──────────────────────────────────────────

def _rule_wrong_side(pipeline_data: dict) -> list[ViolationResult]:
    """Trigger if vehicle trajectory deviates > 120° from legal flow."""
    violations: list[ViolationResult] = []

    tracks = pipeline_data.get("stage_4_tracking", {}).get("tracks", [])
    # Camera config: legal flow vector (dx, dy).  Default = flowing south.
    camera_cfg = pipeline_data.get("camera_config", {})
    legal_vec = camera_cfg.get("legal_flow_vector", [0, 1])
    legal_angle = _vector_angle(legal_vec)

    for track in tracks:
        traj = track.get("trajectory", [])
        if len(traj) < 2:
            continue

        # Compute overall trajectory vector from first to last point
        dx = traj[-1][0] - traj[0][0]
        dy = traj[-1][1] - traj[0][1]

        if dx == 0 and dy == 0:
            continue

        vehicle_angle = _vector_angle([dx, dy])
        angle_diff = abs((vehicle_angle - legal_angle + 180) % 360 - 180)

        if angle_diff > 120:
            violations.append(
                ViolationResult(
                    track_id=track.get("track_id"),
                    vehicle_class=track.get("class"),
                    violation_type="wrong_side_driving",
                    confidence=0.75,  # deterministic geometric rule
                    evidence={
                        "legal_angle": legal_angle,
                        "vehicle_angle": vehicle_angle,
                        "angle_diff": angle_diff,
                        "trajectory": traj,
                    },
                )
            )

    return violations


# ── Rule 4: Stop Line Violation ─────────────────────────────────────────

def _rule_stop_line(pipeline_data: dict) -> list[ViolationResult]:
    """Trigger if traffic light is RED and a vehicle crosses the stop line."""
    violations: list[ViolationResult] = []

    camera_cfg = pipeline_data.get("camera_config", {})
    stop_line = camera_cfg.get("stop_line_polygon")
    if stop_line is None:
        # No stop-line polygon configured for this camera -> skip rule
        return violations

    # Determine traffic light state (mock or real)
    stage2 = pipeline_data.get("stage_2_detection", {})
    light_state = None
    for d in stage2.get("detections", []):
        if d.get("class") == "traffic_light":
            # In mock data the state is absent; production model will add it.
            light_state = d.get("state")
            break

    # Fallback to camera_config if model didn't provide a state
    if light_state is None:
        light_state = camera_cfg.get("traffic_light_state", "green")

    if light_state.lower() != "red":
        return violations

    stage4 = pipeline_data.get("stage_4_tracking", {})
    for track in stage4.get("tracks", []):
        # Check if the bottom edge of the most recent bbox crosses stop line.
        # Simplified: check if the trajectory's last point is inside the stop line polygon.
        traj = track.get("trajectory", [])
        if not traj:
            continue
        last_point = traj[-1]

        # Simple point-in-polygon (ray casting)
        x, y = last_point[0], last_point[1]
        inside = False
        n = len(stop_line)
        for i in range(n):
            x1, y1 = stop_line[i]
            x2, y2 = stop_line[(i + 1) % n]
            if y > min(y1, y2):
                if y <= max(y1, y2):
                    if x <= max(x1, x2):
                        if y1 != y2:
                            xinters = (y - y1) * (x2 - x1) / (y2 - y1) + x1
                        if y1 == y2 or x <= xinters:
                            inside = not inside

        if inside:
            violations.append(
                ViolationResult(
                    track_id=track.get("track_id"),
                    vehicle_class=track.get("class"),
                    violation_type="stop_line",
                    confidence=0.85,
                    evidence={
                        "traffic_light": "RED",
                        "stop_line_polygon": stop_line,
                        "intersection_point": last_point,
                    },
                )
            )

    return violations


# ── Rule 5: Overloading / Protruding Cargo ──────────────────────────────

def _rule_overloading(pipeline_data: dict) -> list[ViolationResult]:
    """Trigger if cargo bounding box exceeds vehicle by >20%% width or >50%% height."""
    violations: list[ViolationResult] = []

    stage2 = pipeline_data.get("stage_2_detection", {})
    # Cargo detections must come from a dedicated stage or be injected in mock
    cargo_items = stage2.get("cargo_detections", [])
    detections = stage2.get("detections", [])

    if not cargo_items:
        return violations

    vehicle_bboxes = {
        tuple(d["bbox"]): d
        for d in detections
        if d.get("class") in ("truck", "auto_rickshaw")
    }

    for cargo in cargo_items:
        cargo_bbox = cargo.get("bbox")
        matched_vehicle = None
        best_iou = 0.0

        for vkey, vehicle in vehicle_bboxes.items():
            i = _iou(cargo_bbox, vehicle["bbox"])
            if i > best_iou:
                best_iou = i
                matched_vehicle = vehicle

        if matched_vehicle is None or best_iou < 0.1:
            continue

        v_bbox = matched_vehicle["bbox"]
        v_w = v_bbox[2] - v_bbox[0]
        v_h = v_bbox[3] - v_bbox[1]
        c_w = cargo_bbox[2] - cargo_bbox[0]
        c_h = cargo_bbox[3] - cargo_bbox[1]

        if c_w > v_w * 1.2 or c_h > v_h * 1.5:
            violations.append(
                ViolationResult(
                    track_id=None,
                    vehicle_class=matched_vehicle.get("class"),
                    violation_type="overloading",
                    confidence=cargo.get("confidence", 0.7),
                    evidence={
                        "cargo_bbox": cargo_bbox,
                        "vehicle_bbox": v_bbox,
                        "cargo_w": c_w,
                        "cargo_h": c_h,
                        "vehicle_w": v_w,
                        "vehicle_h": v_h,
                    },
                )
            )

    return violations


# ── Orchestrator ─────────────────────────────────────────────────────────

def evaluate(pipeline_data: dict) -> dict[str, Any]:
    """Run all 5 rules against the accumulated pipeline data.

    Returns:
        Dict with ``violations_detected`` (list) and ``violation_types`` (list).
    """
    all_violations: list[ViolationResult] = []
    all_violations.extend(_rule_helmet(pipeline_data))
    all_violations.extend(_rule_triple_riding(pipeline_data))
    all_violations.extend(_rule_wrong_side(pipeline_data))
    all_violations.extend(_rule_stop_line(pipeline_data))
    all_violations.extend(_rule_overloading(pipeline_data))

    violation_types = sorted({vT for v in all_violations if (vT := v.violation_type)})

    return {
        "violations_detected": [v.to_dict() for v in all_violations],
        "violation_types": violation_types,
    }
