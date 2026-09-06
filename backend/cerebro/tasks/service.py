from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from cerebro.tasks.models import Task, TaskStatus
from cerebro.tasks.repository import TaskRepository
from cerebro.tasks.state import validate_transition


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def create_task(
        self,
        *,
        job_id: str,
        title: str,
        description: str | None,
        position: int,
    ) -> Task:
        now = datetime.now(timezone.utc)

        task = Task(
            id=str(uuid4()),
            job_id=job_id,
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            position=position,
            created_at=now,
            updated_at=now,
            version=1,
        )

        return self._repository.create(task)

    def get_task(self, task_id: str) -> Task:
        return self._repository.get(task_id)

    def list_tasks_for_job(self, job_id: str) -> list[Task]:
        return self._repository.list_for_job(job_id)

    def transition_task(
        self,
        *,
        task_id: str,
        target: TaskStatus,
    ) -> Task:
        task = self._repository.get(task_id)

        validate_transition(task.status, target)

        return self._repository.transition(
            task,
            target,
            datetime.now(timezone.utc),
        )
