from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    JOB_CREATED = "JOB_CREATED"
    JOB_STATE_CHANGED = "JOB_STATE_CHANGED"
    TASK_CREATED = "TASK_CREATED"
    TASK_STATE_CHANGED = "TASK_STATE_CHANGED"


@dataclass(frozen=True, slots=True)
class Event:
    id: str
    event_type: EventType
    occurred_at: datetime
    job_id: str | None
    task_id: str | None
    payload: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "occurred_at": self.occurred_at.isoformat(),
            "job_id": self.job_id,
            "task_id": self.task_id,
            "payload": self.payload,
        }
