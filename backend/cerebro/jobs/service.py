from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from cerebro.jobs.models import Job, JobStatus
from cerebro.jobs.repository import JobRepository
from cerebro.jobs.state import validate_transition


class JobService:
    def __init__(self, repository: JobRepository) -> None:
        self._repository = repository

    def create_job(self, *, objective: str, project: str) -> Job:
        now = datetime.now(timezone.utc)
        job = Job(
            id=str(uuid4()),
            objective=objective,
            project=project,
            status=JobStatus.CREATED,
            created_at=now,
            updated_at=now,
            version=1,
        )
        return self._repository.create(job)

    def get_job(self, job_id: str) -> Job:
        return self._repository.get(job_id)

    def list_jobs(self) -> list[Job]:
        return self._repository.list()

    def transition_job(self, *, job_id: str, target: JobStatus) -> Job:
        job = self._repository.get(job_id)
        validate_transition(job.status, target)
        return self._repository.transition(
            job,
            target,
            datetime.now(timezone.utc),
        )
