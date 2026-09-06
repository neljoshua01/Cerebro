from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cerebro.api.app import create_app
from cerebro.core.sqlite import SqliteTransaction
from cerebro.events.models import EventType
from cerebro.events.repository import SqliteEventRepository
from cerebro.jobs.models import JobStatus
from cerebro.jobs.repository import (
    JobNotFoundError,
    JobRepository,
    SqliteJobRepository,
)
from cerebro.jobs.service import JobService
from cerebro.jobs.state import InvalidJobTransitionError


def make_service(database_path: Path) -> JobService:
    return JobService(SqliteJobRepository(database_path))


class FakeJobRepository:
    def __init__(self) -> None:
        self.jobs: dict[str, object] = {}

    def create(self, job):
        self.jobs[job.id] = job
        return job

    def get(self, job_id):
        return self.jobs[job_id]

    def list(self):
        return list(self.jobs.values())

    def transition(self, job, target, updated_at):
        updated = job.__class__(
            id=job.id,
            objective=job.objective,
            project=job.project,
            status=target,
            created_at=job.created_at,
            updated_at=updated_at,
            version=job.version + 1,
        )
        self.jobs[job.id] = updated
        return updated


def test_job_service_depends_on_repository_contract() -> None:
    repository = FakeJobRepository()
    service = JobService(repository)

    created = service.create_job(
        objective="Test repository abstraction",
        project="cerebro",
    )

    assert created.status is JobStatus.CREATED
    assert service.get_job(created.id) == created

    transitioned = service.transition_job(
        job_id=created.id,
        target=JobStatus.UNDERSTANDING,
    )

    assert transitioned.status is JobStatus.UNDERSTANDING
    assert transitioned.version == 2


def test_job_survives_service_recreation(tmp_path: Path) -> None:
    database_path = tmp_path / "jobs.sqlite3"
    created = make_service(database_path).create_job(
        objective="Fix the failing test", project="shop-tracker"
    )

    retrieved = make_service(database_path).get_job(created.id)

    assert retrieved == created
    assert retrieved.created_at.tzinfo is not None


def test_state_machine_allows_phase_1a_progression(tmp_path: Path) -> None:
    service = make_service(tmp_path / "jobs.sqlite3")
    job = service.create_job(objective="Build a lifecycle", project="cerebro")

    for target in (
        JobStatus.UNDERSTANDING,
        JobStatus.PLANNING,
        JobStatus.PLAN_READY,
        JobStatus.WAITING_FOR_APPROVAL,
    ):
        previous = job
        job = service.transition_job(job_id=job.id, target=target)
        assert job.status is target
        assert job.version == previous.version + 1
        assert job.updated_at >= previous.updated_at


def test_state_machine_rejects_invalid_and_terminal_transitions(tmp_path: Path) -> None:
    service = make_service(tmp_path / "jobs.sqlite3")
    job = service.create_job(objective="Do not skip stages", project="cerebro")

    with pytest.raises(InvalidJobTransitionError):
        service.transition_job(job_id=job.id, target=JobStatus.PLANNING)

    cancelled = service.transition_job(job_id=job.id, target=JobStatus.CANCELLED)
    with pytest.raises(InvalidJobTransitionError):
        service.transition_job(job_id=cancelled.id, target=JobStatus.UNDERSTANDING)


def test_job_api_create_list_retrieve_and_transition(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "jobs.sqlite3"))

    created_response = client.post(
        "/api/jobs", json={"objective": " Fix a failing test ", "project": " shop-tracker "}
    )

    assert created_response.status_code == 201
    created = created_response.json()
    assert created["objective"] == "Fix a failing test"
    assert created["project"] == "shop-tracker"
    assert created["status"] == "CREATED"
    assert created["version"] == 1
    assert created["created_at"].endswith("Z") or created["created_at"].endswith("+00:00")

    listed_response = client.get("/api/jobs")
    assert listed_response.status_code == 200
    assert [job["id"] for job in listed_response.json()] == [created["id"]]

    retrieved_response = client.get(f"/api/jobs/{created['id']}")
    assert retrieved_response.status_code == 200
    assert retrieved_response.json() == created

    transitioned_response = client.post(
        f"/api/jobs/{created['id']}/transition", json={"target_state": "UNDERSTANDING"}
    )
    assert transitioned_response.status_code == 200
    transitioned = transitioned_response.json()
    assert transitioned["status"] == "UNDERSTANDING"
    assert transitioned["version"] == 2

    event_repository = SqliteEventRepository(tmp_path / "jobs.sqlite3")
    events = event_repository.list(job_id=created["id"])

    assert len(events) == 1

    event = events[0]
    assert event.event_type is EventType.JOB_STATE_CHANGED
    assert event.job_id == created["id"]
    assert event.task_id is None
    assert event.payload == {
        "from_state": "CREATED",
        "to_state": "UNDERSTANDING",
        "version": 2,
    }


def test_job_api_rejects_unknown_jobs_invalid_states_and_invalid_transitions(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "jobs.sqlite3"))

    assert client.get("/api/jobs/missing").status_code == 404
    assert client.post("/api/jobs/missing/transition", json={"target_state": "UNDERSTANDING"}).status_code == 404
    assert client.post("/api/jobs", json={"objective": "   ", "project": "cerebro"}).status_code == 422
    assert client.post("/api/jobs", json={"objective": "valid"}).status_code == 422
    assert client.post(
        "/api/jobs", json={"objective": "valid", "project": "cerebro"}
    ).status_code == 201

    job = client.get("/api/jobs").json()[0]
    assert client.post(
        f"/api/jobs/{job['id']}/transition", json={"target_state": "NOT_A_STATE"}
    ).status_code == 422
    assert client.post(
        f"/api/jobs/{job['id']}/transition", json={"target_state": "COMPLETED"}
    ).status_code == 409

def test_job_repository_create_in_transaction_commits(tmp_path: Path) -> None:
    database_path = tmp_path / "jobs.sqlite3"
    repository = SqliteJobRepository(database_path)

    job = make_service(database_path).create_job(
        objective="Transaction commit test",
        project="cerebro",
    )

    # Remove the normally persisted job so this test specifically exercises
    # the transaction-aware repository method.
    with SqliteTransaction(database_path) as connection:
        connection.execute("DELETE FROM jobs WHERE id = ?", (job.id,))

        repository.create_in_transaction(connection, job)

    retrieved = repository.get(job.id)

    assert retrieved == job


def test_job_repository_create_in_transaction_rolls_back(tmp_path: Path) -> None:
    database_path = tmp_path / "jobs.sqlite3"
    repository = SqliteJobRepository(database_path)

    job = make_service(database_path).create_job(
        objective="Transaction rollback test",
        project="cerebro",
    )

    with SqliteTransaction(database_path) as connection:
        connection.execute("DELETE FROM jobs WHERE id = ?", (job.id,))

    with pytest.raises(RuntimeError):
        with SqliteTransaction(database_path) as connection:
            repository.create_in_transaction(connection, job)

            raise RuntimeError("force rollback")

    with pytest.raises(JobNotFoundError):
        repository.get(job.id)


def test_job_repository_transition_in_transaction_rolls_back(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "jobs.sqlite3"
    repository = SqliteJobRepository(database_path)

    job = make_service(database_path).create_job(
        objective="Transaction transition test",
        project="cerebro",
    )

    with pytest.raises(RuntimeError):
        with SqliteTransaction(database_path) as connection:
            transitioned = repository.transition_in_transaction(
                connection,
                job,
                JobStatus.UNDERSTANDING,
                job.updated_at,
            )

            assert transitioned.status is JobStatus.UNDERSTANDING
            assert transitioned.version == 2

            raise RuntimeError("force rollback")

    persisted = repository.get(job.id)

    assert persisted.status is JobStatus.CREATED
    assert persisted.version == 1


def test_transition_job_with_event_commits_atomically(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "cerebro.sqlite3"

    job_repository = SqliteJobRepository(database_path)
    event_repository = SqliteEventRepository(database_path)
    service = JobService(job_repository)

    job = service.create_job(
        objective="Test atomic Job and Event persistence",
        project="cerebro",
    )

    transitioned, event = service.transition_job_with_event(
        job_id=job.id,
        target=JobStatus.UNDERSTANDING,
        event_repository=event_repository,
        transaction=SqliteTransaction(database_path),
    )

    assert transitioned.status is JobStatus.UNDERSTANDING
    assert transitioned.version == 2

    persisted_job = job_repository.get(job.id)
    persisted_event = event_repository.get(event.id)

    assert persisted_job == transitioned
    assert persisted_event == event

    assert event.event_type is EventType.JOB_STATE_CHANGED
    assert event.job_id == job.id
    assert event.payload == {
        "from_state": "CREATED",
        "to_state": "UNDERSTANDING",
        "version": 2,
    }


def test_transition_job_with_event_rolls_back_job_when_event_fails(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "cerebro.sqlite3"

    job_repository = SqliteJobRepository(database_path)
    service = JobService(job_repository)

    job = service.create_job(
        objective="Test atomic rollback",
        project="cerebro",
    )

    class FailingEventRepository:
        def create_in_transaction(self, connection, event):
            raise RuntimeError("forced event failure")

    with pytest.raises(RuntimeError, match="forced event failure"):
        service.transition_job_with_event(
            job_id=job.id,
            target=JobStatus.UNDERSTANDING,
            event_repository=FailingEventRepository(),
            transaction=SqliteTransaction(database_path),
        )

    persisted_job = job_repository.get(job.id)

    assert persisted_job.status is JobStatus.CREATED
    assert persisted_job.version == 1

def test_transition_job_emits_event_atomically(tmp_path: Path) -> None:
    database_path = tmp_path / "cerebro.sqlite3"

    job_repository = SqliteJobRepository(database_path)
    event_repository = SqliteEventRepository(database_path)
    transaction = SqliteTransaction(database_path)

    service = JobService(
        job_repository,
        event_repository,
        transaction,
    )

    job = service.create_job(
        objective="Test atomic transition",
        project="cerebro",
    )

    transitioned = service.transition_job(
        job_id=job.id,
        target=JobStatus.UNDERSTANDING,
    )

    assert transitioned.status == JobStatus.UNDERSTANDING

    events = event_repository.list(job_id=job.id)

    assert len(events) == 1

    event = events[0]
    assert event.event_type == EventType.JOB_STATE_CHANGED
    assert event.job_id == job.id
    assert event.task_id is None
    assert event.payload == {
        "from_state": "CREATED",
        "to_state": "UNDERSTANDING",
        "version": 2,
    }


def test_transition_job_rolls_back_when_event_fails(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "cerebro.sqlite3"

    job_repository = SqliteJobRepository(database_path)

    class FailingEventRepository:
        def create_in_transaction(self, connection, event):
            raise RuntimeError("forced event failure")

    service = JobService(
        job_repository,
        FailingEventRepository(),
        SqliteTransaction(database_path),
    )

    job = service.create_job(
        objective="Test normal transition rollback",
        project="cerebro",
    )

    with pytest.raises(RuntimeError, match="forced event failure"):
        service.transition_job(
            job_id=job.id,
            target=JobStatus.UNDERSTANDING,
        )

    persisted_job = job_repository.get(job.id)

    assert persisted_job.status is JobStatus.CREATED
    assert persisted_job.version == 1
