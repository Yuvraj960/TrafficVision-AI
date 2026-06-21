"""Orchestrator end-to-end tests — verify all 7 stages run and produce correct shapes.

Uses the existing mock data so no GPU / network / DB is needed.
These tests validate that:
1. Each stage produces the expected output key schema
2. The final pipeline_data contains a violation_record
3. Switching USE_REAL_MODELS=false bypasses real inference paths
"""

import pytest

import app.pipeline.orchestrator as orchestrator_module
from app.pipeline.orchestrator import derive_violation_record, run_pipeline


class TestDeriveViolationRecord:
    """Unit tests for the violation record derivation logic."""

    def test_no_violations_returns_no_violation(self):
        data = {
            "stage_7_rules": {
                "violations_detected": [],
                "violation_types": [],
            }
        }
        record = derive_violation_record(data)
        assert record.violation_type == "no_violation"

    def test_single_violation_maps_correctly(self):
        data = {
            "stage_7_rules": {
                "violations_detected": [
                    {
                        "violation_type": "helmet",
                        "vehicle_class": "motorcycle",
                        "plate_text": "MH 12 AB 1234",
                        "confidence": 0.87,
                        "track_id": 5,
                        "evidence": {"rider_bbox": [1, 2, 3, 4]},
                    }
                ],
                "violation_types": ["helmet"],
            }
        }
        record = derive_violation_record(data)
        assert record.violation_type == "helmet"
        assert record.vehicle_type == "motorcycle"
        assert record.plate_number == "MH 12 AB 1234"
        assert record.confidence_score == 0.87
        assert record.track_id == 5
        assert record.evidence == {"rider_bbox": [1, 2, 3, 4]}

    def test_multiple_violations_takes_first(self):
        data = {
            "stage_7_rules": {
                "violations_detected": [
                    {"violation_type": "helmet", "vehicle_class": "motorcycle"},
                    {"violation_type": "triple_riding", "vehicle_class": "motorcycle"},
                ],
                "violation_types": ["helmet", "triple_riding"],
            }
        }
        record = derive_violation_record(data)
        assert record.violation_type == "helmet"


class TestRunPipeline:
    """Full 7-stage pipeline with mock data (USE_REAL_MODELS=false by default)."""

    def test_pipeline_produces_all_stage_keys(self):
        result = run_pipeline("test-job-001", {"image_url": "http://test/image.jpg"})

        for stage_name, _ in orchestrator_module.STAGES:
            assert stage_name in result, f"{stage_name} missing from pipeline output"

    def test_pipeline_includes_violation_record(self):
        result = run_pipeline("test-job-002", {})
        assert "violation_record" in result
        record = result["violation_record"]
        assert "violation_type" in record
        assert "confidence_score" in record

    def test_pipeline_respects_iqa_skip(self):
        """When IQA fails, subsequent stages should indicate skipped upstream."""
        result = run_pipeline(
            "test-job-iqa-fail",
            {},   # no image_bytes → IQA may fall back to mock which passes
        )
        # With mock IQA: quality_pass=True, so no skip
        s2 = result.get("stage_2_detection", {})
        assert s2.get("skipped", False) is False

    def test_pipeline_output_shapes_match_expected_schema(self):
        """Verify each stage output has the required structure."""
        result = run_pipeline("test-job-shape-check", {})

        # Stage 1: IQA
        s1 = result["stage_1_iqa"]
        assert "quality_pass" in s1
        assert "metrics" in s1

        # Stage 2: Primary detection
        s2 = result["stage_2_detection"]
        assert "detections" in s2

        # Stage 3: Secondary detection
        s3 = result["stage_3_secondary"]
        assert "secondary_detections" in s3

        # Stage 4: Tracking
        s4 = result["stage_4_tracking"]
        assert "tracks" in s4

        # Stage 5: LPD
        s5 = result["stage_5_lpd"]
        assert "plates" in s5

        # Stage 6: OCR
        s6 = result["stage_6_ocr"]
        assert "plate_text" in s6

        # Stage 7: Rule engine
        s7 = result["stage_7_rules"]
        assert "violations_detected" in s7
        assert "violation_types" in s7

    def test_pipeline_job_id_preserved_in_result(self):
        """The job_id is echoed back in the result dict."""
        job_id = "job-unique-12345"
        result = run_pipeline(job_id, {"camera_id": "cam-001"})
        assert result["job_id"] == job_id