from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class Task:
    id: str
    job_id: str
    title: str
    description: str | None
    status: TaskStatus
    position: int
    created_at: datetime
    updated_at: datetime
    version: int
