from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from cerebro.core.sqlite import SqliteTransaction
from cerebro.events.models import Event, EventType
from cerebro.events.repository import (
    EventConflictError,
    EventNotFoundError,
    SqliteEventRepository,
)


def make_event(
    event_id: str,
    *,
    occurred_at: datetime,
    job_id: str | None = None,
    task_id: str | None = None,
    payload: dict[str, object] | None = None,
    event_type: EventType = EventType.JOB_STATE_CHANGED,
) -> Event:
    return Event(
        id=event_id,
        event_type=event_type,
        occurred_at=occurred_at,
        job_id=job_id,
        task_id=task_id,
        payload=payload or {},
    )


def test_event_can_be_persisted_and_retrieved(tmp_path: Path) -> None:
    repository = SqliteEventRepository(tmp_path / "events.sqlite3")
    occurred_at = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)
    event = make_event(
        "event-1",
        occurred_at=occurred_at,
        job_id="job-1",
        payload={"from": "CREATED", "to": "UNDERSTANDING"},
    )

    created = repository.create(event)

    assert created == event
    assert repository.get("event-1") == event


def test_missing_event_raises_not_found(tmp_path: Path) -> None:
    repository = SqliteEventRepository(tmp_path / "events.sqlite3")

    with pytest.raises(EventNotFoundError):
        repository.get("missing-event")


def test_payload_survives_json_round_trip(tmp_path: Path) -> None:
    repository = SqliteEventRepository(tmp_path / "events.sqlite3")
    event = make_event(
        "event-payload",
        occurred_at=datetime(2026, 9, 6, 10, 1, tzinfo=timezone.utc),
        payload={
            "from": "CREATED",
            "to": "PLANNING",
            "details": {"reason": "approved"},
            "attempt": 2,
        },
    )

    repository.create(event)
    retrieved = repository.get(event.id)

    assert retrieved.payload == {
        "from": "CREATED",
        "to": "PLANNING",
        "details": {"reason": "approved"},
        "attempt": 2,
    }


def test_optional_references_are_supported(tmp_path: Path) -> None:
    repository = SqliteEventRepository(tmp_path / "events.sqlite3")
    occurred_at = datetime(2026, 9, 6, 10, 2, tzinfo=timezone.utc)

    job_only = make_event(
        "event-job-only",
        occurred_at=occurred_at,
        job_id="job-1",
    )
    task_only = make_event(
        "event-task-only",
        occurred_at=occurred_at,
        task_id="task-1",
        event_type=EventType.TASK_STATE_CHANGED,
    )
    unscoped = make_event(
        "event-unscoped",
        occurred_at=occurred_at,
    )
    both = make_event(
        "event-both",
        occurred_at=occurred_at,
        job_id="job-1",
        task_id="task-1",
        event_type=EventType.TASK_STATE_CHANGED,
    )

    repository.create(job_only)
    repository.create(task_only)
    repository.create(unscoped)
    repository.create(both)

    assert repository.get("event-job-only").task_id is None
    assert repository.get("event-task-only").job_id is None
    assert repository.get("event-unscoped").job_id is None
    assert repository.get("event-unscoped").task_id is None
    assert repository.get("event-both").job_id == "job-1"
    assert repository.get("event-both").task_id == "task-1"


def test_events_are_ordered_by_occurred_at_then_id(tmp_path: Path) -> None:
    repository = SqliteEventRepository(tmp_path / "events.sqlite3")
    timestamp = datetime(2026, 9, 6, 10, 3, tzinfo=timezone.utc)

    repository.create(make_event("b", occurred_at=timestamp))
    repository.create(make_event("a", occurred_at=timestamp))
    repository.create(
        make_event(
            "c",
            occurred_at=datetime(2026, 9, 6, 10, 2, tzinfo=timezone.utc),
        )
    )

    events = repository.list()

    assert [event.id for event in events] == ["c", "a", "b"]


def test_events_can_be_filtered_by_job(tmp_path: Path) -> None:
    repository = SqliteEventRepository(tmp_path / "events.sqlite3")
    timestamp = datetime(2026, 9, 6, 10, 4, tzinfo=timezone.utc)

    repository.create(make_event("job-a-1", occurred_at=timestamp, job_id="job-a"))
    repository.create(make_event("job-b-1", occurred_at=timestamp, job_id="job-b"))
    repository.create(make_event("job-a-2", occurred_at=timestamp, job_id="job-a"))

    events = repository.list(job_id="job-a")

    assert [event.id for event in events] == ["job-a-1", "job-a-2"]
    assert all(event.job_id == "job-a" for event in events)


def test_events_can_be_filtered_by_task(tmp_path: Path) -> None:
    repository = SqliteEventRepository(tmp_path / "events.sqlite3")
    timestamp = datetime(2026, 9, 6, 10, 5, tzinfo=timezone.utc)

    repository.create(make_event("task-a-1", occurred_at=timestamp, task_id="task-a"))
    repository.create(make_event("task-b-1", occurred_at=timestamp, task_id="task-b"))
    repository.create(make_event("task-a-2", occurred_at=timestamp, task_id="task-a"))

    events = repository.list(task_id="task-a")

    assert [event.id for event in events] == ["task-a-1", "task-a-2"]
    assert all(event.task_id == "task-a" for event in events)


def test_events_can_be_filtered_by_job_and_task(tmp_path: Path) -> None:
    repository = SqliteEventRepository(tmp_path / "events.sqlite3")
    timestamp = datetime(2026, 9, 6, 10, 6, tzinfo=timezone.utc)

    repository.create(
        make_event(
            "both-match",
            occurred_at=timestamp,
            job_id="job-a",
            task_id="task-a",
        )
    )
    repository.create(
        make_event(
            "job-match-only",
            occurred_at=timestamp,
            job_id="job-a",
            task_id="task-b",
        )
    )

    events = repository.list(job_id="job-a", task_id="task-a")

    assert [event.id for event in events] == ["both-match"]


def test_event_persists_across_repository_instances(tmp_path: Path) -> None:
    database_path = tmp_path / "events.sqlite3"
    event = make_event(
        "persistent-event",
        occurred_at=datetime(2026, 9, 6, 10, 7, tzinfo=timezone.utc),
        job_id="job-persistent",
        task_id="task-persistent",
        payload={"status": "READY"},
    )

    repository_one = SqliteEventRepository(database_path)
    repository_one.create(event)

    repository_two = SqliteEventRepository(database_path)

    assert repository_two.get(event.id) == event


def test_event_repository_create_in_transaction_commits(tmp_path: Path) -> None:
    database_path = tmp_path / "events.sqlite3"
    repository = SqliteEventRepository(database_path)

    event = make_event(
        "transaction-event",
        occurred_at=datetime(2026, 9, 6, 10, 9, tzinfo=timezone.utc),
    )

    with SqliteTransaction(database_path) as connection:
        repository.create_in_transaction(connection, event)

    assert repository.get(event.id) == event


def test_event_repository_create_in_transaction_rolls_back(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "events.sqlite3"
    repository = SqliteEventRepository(database_path)

    event = make_event(
        "rollback-event",
        occurred_at=datetime(2026, 9, 6, 10, 10, tzinfo=timezone.utc),
    )

    with pytest.raises(RuntimeError):
        with SqliteTransaction(database_path) as connection:
            repository.create_in_transaction(connection, event)
            raise RuntimeError("force rollback")

    with pytest.raises(EventNotFoundError):
        repository.get(event.id)


def test_duplicate_event_id_raises_conflict(tmp_path: Path) -> None:
    repository = SqliteEventRepository(tmp_path / "events.sqlite3")
    event = make_event(
        "duplicate-event",
        occurred_at=datetime(2026, 9, 6, 10, 8, tzinfo=timezone.utc),
    )

    repository.create(event)

    with pytest.raises(EventConflictError):
        repository.create(event)
