"""Pipeline orchestrator – runs every CV stage in sequence.

Each stage receives the accumulated data from all preceding stages and
returns its own results. The orchestrator also derives a single
:class:`ViolationRecord` from the final stage output – this is the
canonical result that gets written back to the database.
"""

import logging
from dataclasses import asdict, dataclass, field
from typing import Any

from app.pipeline.stage_1_iqa import run_stage_1
from app.pipeline.stage_2_detection import run_stage_2
from app.pipeline.stage_3_secondary import run_stage_3
from app.pipeline.stage_4_tracking import run_stage_4
from app.pipeline.stage_5_lpd import run_stage_5
from app.pipeline.stage_6_ocr import run_stage_6
from app.pipeline.stage_7_rules import run_stage_7

logger = logging.getLogger(__name__)

STAGES = [
    ("stage_1_iqa", run_stage_1),
    ("stage_2_detection", run_stage_2),
    ("stage_3_secondary", run_stage_3),
    ("stage_4_tracking", run_stage_4),
    ("stage_5_lpd", run_stage_5),
    ("stage_6_ocr", run_stage_6),
    ("stage_7_rules", run_stage_7),
]


@dataclass
class ViolationRecord:
    """Final, classified violation resulting from the pipeline."""

    violation_type: str = "unknown"
    vehicle_type: str | None = None
    plate_number: str | None = None
    confidence_score: float | None = None
    plate_image_url: str | None = None
    track_id: int | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None or k == "evidence"}


def derive_violation_record(pipeline_data: dict[str, Any]) -> ViolationRecord:
    """Pull the single best violation out of the Stage 7 results."""
    rules = pipeline_data.get("stage_7_rules", {})
    violations = rules.get("violations_detected") or []

    if not violations:
        # Mock fallback: synthesize one rule decision so the worker still
        # produces a row even when the mock returns an empty list.
        return ViolationRecord(
            violation_type="no_violation",
            vehicle_type=None,
            plate_number=None,
            confidence_score=0.0,
        )

    first = violations[0]
    return ViolationRecord(
        violation_type=first.get("violation_type", "unknown"),
        vehicle_type=first.get("vehicle_class"),
        plate_number=first.get("plate_text"),
        confidence_score=float(first.get("confidence", 0.0)),
        track_id=first.get("track_id"),
        evidence=first.get("evidence", {}),
    )


def run_pipeline(job_id: str, image_data: dict) -> dict:
    """Execute the seven-stage CV pipeline sequentially.

    Args:
        job_id: Unique job identifier.
        image_data: Camera / ingestion metadata.

    Returns:
        Dict containing the accumulated output of all 7 stages plus a
        derived `violation_record` ready for DB persistence.
    """
    pipeline_data: dict[str, Any] = {"job_id": job_id, **image_data}

    for stage_name, stage_fn in STAGES:
        logger.info("job=%s  ->  %s", job_id, stage_name)
        stage_output = stage_fn(pipeline_data)
        pipeline_data[stage_name] = stage_output
        logger.info("job=%s  ok  %s", job_id, stage_name)

    record = derive_violation_record(pipeline_data)
    pipeline_data["violation_record"] = record.to_dict()
    logger.info("job=%s  pipeline complete -> %s", job_id, pipeline_data["violation_record"])
    return pipeline_data
