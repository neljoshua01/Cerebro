from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cerebro.api.app import create_app
from cerebro.jobs.models import JobStatus
from cerebro.jobs.repository import JobRepository, SqliteJobRepository
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
