from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Protocol

from cerebro.events.models import Event, EventType


class EventRepository(Protocol):
    def create(self, event: Event) -> Event:
        ...

    def get(self, event_id: str) -> Event:
        ...

    def list(
        self,
        *,
        job_id: str | None = None,
        task_id: str | None = None,
    ) -> list[Event]:
        ...


class EventNotFoundError(LookupError):
    def __init__(self, event_id: str) -> None:
        super().__init__(f"Event '{event_id}' was not found.")
        self.event_id = event_id


class EventConflictError(RuntimeError):
    """Raised when an event cannot be persisted because of a conflict."""


class SqliteEventRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    job_id TEXT,
                    task_id TEXT,
                    payload TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_occurred_at "
                "ON events(occurred_at, id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_job_occurred_at "
                "ON events(job_id, occurred_at, id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_task_occurred_at "
                "ON events(task_id, occurred_at, id)"
            )

    def create(self, event: Event) -> Event:
        payload = json.dumps(event.payload)

        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO events (
                        id,
                        event_type,
                        occurred_at,
                        job_id,
                        task_id,
                        payload
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """
                    ,
                    (
                        event.id,
                        event.event_type.value,
                        event.occurred_at.isoformat(),
                        event.job_id,
                        event.task_id,
                        payload,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise EventConflictError(
                f"Event '{event.id}' could not be persisted."
            ) from error

        return event

    def get(self, event_id: str) -> Event:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM events WHERE id = ?",
                (event_id,),
            ).fetchone()

        if row is None:
            raise EventNotFoundError(event_id)

        return _to_event(row)

    def list(
        self,
        *,
        job_id: str | None = None,
        task_id: str | None = None,
    ) -> list[Event]:
        query = "SELECT * FROM events"
        conditions: list[str] = []
        parameters: list[str] = []

        if job_id is not None:
            conditions.append("job_id = ?")
            parameters.append(job_id)

        if task_id is not None:
            conditions.append("task_id = ?")
            parameters.append(task_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY occurred_at ASC, id ASC"

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        return [_to_event(row) for row in rows]


def _to_event(row: sqlite3.Row) -> Event:
    return Event(
        id=row["id"],
        event_type=EventType(row["event_type"]),
        occurred_at=datetime.fromisoformat(row["occurred_at"]),
        job_id=row["job_id"],
        task_id=row["task_id"],
        payload=json.loads(row["payload"]),
    )
