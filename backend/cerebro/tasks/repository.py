from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Protocol

from cerebro.tasks.models import Task, TaskStatus


class TaskRepository(Protocol):
    def create(self, task: Task) -> Task:
        ...

    def get(self, task_id: str) -> Task:
        ...

    def list_for_job(self, job_id: str) -> list[Task]:
        ...

    def transition(
        self,
        task: Task,
        target: TaskStatus,
        updated_at: datetime,
    ) -> Task:
        ...


class TaskNotFoundError(LookupError):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task '{task_id}' was not found.")
        self.task_id = task_id


class TaskConcurrencyError(RuntimeError):
    """Raised when a concurrent update changed a task before this update."""


class SqliteTaskRepository:
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
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_job_position "
                "ON tasks(job_id, position)"
            )

    def create(self, task: Task) -> Task:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tasks (
                    id,
                    job_id,
                    title,
                    description,
                    status,
                    position,
                    created_at,
                    updated_at,
                    version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                ,
                (
                    task.id,
                    task.job_id,
                    task.title,
                    task.description,
                    task.status.value,
                    task.position,
                    _serialize_timestamp(task.created_at),
                    _serialize_timestamp(task.updated_at),
                    task.version,
                ),
            )

        return task

    def get(self, task_id: str) -> Task:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()

        if row is None:
            raise TaskNotFoundError(task_id)

        return _to_task(row)

    def list_for_job(self, job_id: str) -> list[Task]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM tasks
                WHERE job_id = ?
                ORDER BY position ASC, id ASC
                """
                ,
                (job_id,),
            ).fetchall()

        return [_to_task(row) for row in rows]

    def transition(
        self,
        task: Task,
        target: TaskStatus,
        updated_at: datetime,
    ) -> Task:
        new_version = task.version + 1

        with self._connect() as connection:
            result = connection.execute(
                """
                UPDATE tasks
                SET status = ?, updated_at = ?, version = ?
                WHERE id = ?
                  AND version = ?
                  AND status = ?
                """
                ,
                (
                    target.value,
                    _serialize_timestamp(updated_at),
                    new_version,
                    task.id,
                    task.version,
                    task.status.value,
                ),
            )

        if result.rowcount != 1:
            raise TaskConcurrencyError(
                f"Task '{task.id}' changed before the transition could be persisted."
            )

        return Task(
            id=task.id,
            job_id=task.job_id,
            title=task.title,
            description=task.description,
            status=target,
            position=task.position,
            created_at=task.created_at,
            updated_at=updated_at,
            version=new_version,
        )


def _serialize_timestamp(value: datetime) -> str:
    return value.isoformat()


def _to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"],
        job_id=row["job_id"],
        title=row["title"],
        description=row["description"],
        status=TaskStatus(row["status"]),
        position=row["position"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        version=row["version"],
    )
