"""Stage 7 – Violation Decision Engine.

Runs the deterministic rule engine from `rule_engine.py` over all
upstream stage outputs.  This is the only stage that the orchestrator
uses to derive the final :class:`ViolationRecord`.
"""

from app.pipeline import rule_engine as _engine


def run_stage_7(data: dict) -> dict:
    """Run the violation decision engine over all pipeline outputs.

    Args:
        data: Cumulative pipeline data (all preceding stage results).

    Returns:
        Rules result dict with ``violations_detected`` and ``violation_types``.
    """
    return _engine.evaluate(data)
