from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from cerebro.jobs.repository import JobNotFoundError
from cerebro.jobs.service import JobService
from cerebro.jobs.repository import JobRepository
from cerebro.tasks.models import Task, TaskStatus
from cerebro.tasks.repository import TaskConcurrencyError, TaskNotFoundError
from cerebro.tasks.service import TaskService
from cerebro.tasks.state import InvalidTaskTransitionError

router = APIRouter(prefix="/api", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    position: int = Field(ge=1)

    @field_validator("title")
    @classmethod
    def reject_blank_title(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Title must not be blank.")

        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None


class TransitionTaskRequest(BaseModel):
    target_state: TaskStatus


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    title: str
    description: str | None
    status: TaskStatus
    position: int
    created_at: datetime
    updated_at: datetime
    version: int


def _task_service(request: Request) -> TaskService:
    return request.app.state.task_service


def _job_service(request: Request) -> JobService:
    return request.app.state.job_service


@router.post(
    "/jobs/{job_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    job_id: str,
    payload: CreateTaskRequest,
    request: Request,
) -> Task:
    try:
        _job_service(request).get_job(job_id)
    except JobNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return _task_service(request).create_task(
        job_id=job_id,
        title=payload.title,
        description=payload.description,
        position=payload.position,
    )


@router.get(
    "/jobs/{job_id}/tasks",
    response_model=list[TaskResponse],
)
def list_tasks(
    job_id: str,
    request: Request,
) -> list[Task]:
    try:
        _job_service(request).get_job(job_id)
    except JobNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return _task_service(request).list_tasks_for_job(job_id)


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
)
def get_task(
    task_id: str,
    request: Request,
) -> Task:
    try:
        return _task_service(request).get_task(task_id)
    except TaskNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error


@router.post(
    "/tasks/{task_id}/transition",
    response_model=TaskResponse,
)
def transition_task(
    task_id: str,
    payload: TransitionTaskRequest,
    request: Request,
) -> Task:
    try:
        return _task_service(request).transition_task(
            task_id=task_id,
            target=payload.target_state,
        )
    except TaskNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except InvalidTaskTransitionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except TaskConcurrencyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task changed concurrently; retrieve it and retry.",
        ) from error
