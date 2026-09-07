from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PlanStatus(str, Enum):
    DRAFT = "DRAFT"
    READY = "READY"


@dataclass(frozen=True, slots=True)
class Plan:
    id: str
    job_id: str
    objective: str
    status: PlanStatus
    created_at: datetime
    updated_at: datetime
    version: int
