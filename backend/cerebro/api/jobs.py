from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from cerebro.jobs.models import Job, JobStatus
from cerebro.jobs.repository import JobConcurrencyError, JobNotFoundError
from cerebro.jobs.service import JobService
from cerebro.jobs.state import InvalidJobTransitionError

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class CreateJobRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=10_000)
    project: str = Field(min_length=1, max_length=255)

    @field_validator("objective", "project")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank.")
        return value


class TransitionJobRequest(BaseModel):
    target_state: JobStatus


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    objective: str
    project: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    version: int


def _service(request: Request) -> JobService:
    return request.app.state.job_service


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(payload: CreateJobRequest, request: Request) -> Job:
    return _service(request).create_job(objective=payload.objective, project=payload.project)


@router.get("", response_model=list[JobResponse])
def list_jobs(request: Request) -> list[Job]:
    return _service(request).list_jobs()


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, request: Request) -> Job:
    try:
        return _service(request).get_job(job_id)
    except JobNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/{job_id}/transition", response_model=JobResponse)
def transition_job(job_id: str, payload: TransitionJobRequest, request: Request) -> Job:
    try:
        return _service(request).transition_job(job_id=job_id, target=payload.target_state)
    except JobNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except InvalidJobTransitionError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except JobConcurrencyError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job changed concurrently; retrieve it and retry.") from error
