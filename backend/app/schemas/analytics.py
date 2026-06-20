from pydantic import BaseModel
from typing import Dict


class AnalyticsSummary(BaseModel):
    total_violations: int
    by_type: Dict[str, int]
