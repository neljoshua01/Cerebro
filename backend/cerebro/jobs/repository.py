from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Protocol

from cerebro.jobs.models import Job, JobStatus


class JobRepository(Protocol):
    def create(self, job: Job) -> Job: ...

    def get(self, job_id: str) -> Job: ...

    def list(self) -> list[Job]: ...

    def transition(
        self,
        job: Job,
        target: JobStatus,
        updated_at: datetime,
    ) -> Job: ...


class JobNotFoundError(LookupError):
    def __init__(self, job_id: str) -> None:
        super().__init__(f"Job '{job_id}' was not found.")
        self.job_id = job_id


class JobConcurrencyError(RuntimeError):
    """Raised when a concurrent update changed a job before this update."""


class SqliteJobRepository:
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
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    objective TEXT NOT NULL,
                    project TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_created_at "
                "ON jobs(created_at, id)"
            )

    def create(self, job: Job) -> Job:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (id, objective, project, status, created_at, updated_at, version)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.objective,
                    job.project,
                    job.status.value,
                    _serialize_timestamp(job.created_at),
                    _serialize_timestamp(job.updated_at),
                    job.version,
                ),
            )
        return job

    def create_in_transaction(
        self,
        connection: sqlite3.Connection,
        job: Job,
    ) -> Job:
        connection.execute(
            """
            INSERT INTO jobs (
                id,
                objective,
                project,
                status,
                created_at,
                updated_at,
                version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                job.objective,
                job.project,
                job.status.value,
                _serialize_timestamp(job.created_at),
                _serialize_timestamp(job.updated_at),
                job.version,
            ),
        )
        return job

    def get(self, job_id: str) -> Job:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()

        if row is None:
            raise JobNotFoundError(job_id)

        return _to_job(row)

    def list(self) -> list[Job]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs ORDER BY created_at ASC, id ASC"
            ).fetchall()

        return [_to_job(row) for row in rows]

    def transition(
        self,
        job: Job,
        target: JobStatus,
        updated_at: datetime,
    ) -> Job:
        new_version = job.version + 1

        with self._connect() as connection:
            result = connection.execute(
                """
                UPDATE jobs
                SET status = ?, updated_at = ?, version = ?
                WHERE id = ? AND version = ? AND status = ?
                """,
                (
                    target.value,
                    _serialize_timestamp(updated_at),
                    new_version,
                    job.id,
                    job.version,
                    job.status.value,
                ),
            )

        if result.rowcount != 1:
            raise JobConcurrencyError(
                f"Job '{job.id}' changed before the transition could be persisted."
            )

        return Job(
            id=job.id,
            objective=job.objective,
            project=job.project,
            status=target,
            created_at=job.created_at,
            updated_at=updated_at,
            version=new_version,
        )

    def transition_in_transaction(
        self,
        connection: sqlite3.Connection,
        job: Job,
        target: JobStatus,
        updated_at: datetime,
    ) -> Job:
        new_version = job.version + 1

        result = connection.execute(
            """
            UPDATE jobs
            SET status = ?, updated_at = ?, version = ?
            WHERE id = ? AND version = ? AND status = ?
            """,
            (
                target.value,
                _serialize_timestamp(updated_at),
                new_version,
                job.id,
                job.version,
                job.status.value,
            ),
        )

        if result.rowcount != 1:
            raise JobConcurrencyError(
                f"Job '{job.id}' changed before the transition could be persisted."
            )

        return Job(
            id=job.id,
            objective=job.objective,
            project=job.project,
            status=target,
            created_at=job.created_at,
            updated_at=updated_at,
            version=new_version,
        )


def _serialize_timestamp(value: datetime) -> str:
    return value.isoformat()


def _to_job(row: sqlite3.Row) -> Job:
    return Job(
        id=row["id"],
        objective=row["objective"],
        project=row["project"],
        status=JobStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        version=row["version"],
    )
