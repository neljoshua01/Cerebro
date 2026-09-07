from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cerebro.plans.models import Plan, PlanStatus
from cerebro.plans.repository import (
    PlanConcurrencyError,
    PlanNotFoundError,
    SqlitePlanRepository,
)
from cerebro.plans.state import InvalidPlanTransitionError, validate_transition


def make_plan() -> Plan:
    timestamp = datetime.now(timezone.utc)
    return Plan(
        id="plan-123",
        job_id="job-123",
        objective="Test Plan",
        status=PlanStatus.DRAFT,
        created_at=timestamp,
        updated_at=timestamp,
        version=1,
    )


def test_plan_can_be_constructed() -> None:
    plan = make_plan()

    assert plan.id == "plan-123"
    assert plan.job_id == "job-123"
    assert plan.objective == "Test Plan"
    assert plan.status is PlanStatus.DRAFT
    assert plan.created_at.tzinfo is not None
    assert plan.updated_at.tzinfo is not None
    assert plan.version == 1


def test_plan_is_immutable() -> None:
    plan = make_plan()

    with pytest.raises(FrozenInstanceError):
        plan.status = PlanStatus.READY


def test_draft_to_ready_is_valid() -> None:
    validate_transition(PlanStatus.DRAFT, PlanStatus.READY)


def test_ready_cannot_transition() -> None:
    with pytest.raises(InvalidPlanTransitionError):
        validate_transition(PlanStatus.READY, PlanStatus.DRAFT)

    with pytest.raises(InvalidPlanTransitionError):
        validate_transition(PlanStatus.READY, PlanStatus.READY)


def test_invalid_transition_raises_domain_error_with_states() -> None:
    with pytest.raises(
        InvalidPlanTransitionError,
        match="Cannot transition a plan from READY to DRAFT.",
    ) as error_info:
        validate_transition(PlanStatus.READY, PlanStatus.DRAFT)

    assert error_info.value.current is PlanStatus.READY
    assert error_info.value.target is PlanStatus.DRAFT


def test_plan_status_is_string_enum() -> None:
    assert PlanStatus.DRAFT.value == "DRAFT"
    assert PlanStatus.READY.value == "READY"


def test_plan_repository_create_and_get(tmp_path: Path) -> None:
    database_path = tmp_path / "plans.sqlite3"
    repository = SqlitePlanRepository(database_path)

    plan = make_plan()

    created = repository.create(plan)
    retrieved = repository.get(plan.id)

    assert created == plan
    assert retrieved == plan


def test_plan_repository_list_for_job(tmp_path: Path) -> None:
    database_path = tmp_path / "plans.sqlite3"
    repository = SqlitePlanRepository(database_path)

    timestamp = datetime.now(timezone.utc)

    first = Plan(
        id="plan-1",
        job_id="job-123",
        objective="First Plan",
        status=PlanStatus.DRAFT,
        created_at=timestamp,
        updated_at=timestamp,
        version=1,
    )

    second_timestamp = timestamp + timedelta(microseconds=1)

    second = Plan(
        id="plan-2",
        job_id="job-123",
        objective="Second Plan",
        status=PlanStatus.READY,
        created_at=second_timestamp,
        updated_at=second_timestamp,
        version=2,
    )

    other_job = Plan(
        id="plan-3",
        job_id="job-other",
        objective="Other Job Plan",
        status=PlanStatus.DRAFT,
        created_at=second_timestamp,
        updated_at=second_timestamp,
        version=1,
    )

    repository.create(first)
    repository.create(second)
    repository.create(other_job)

    plans = repository.list_for_job("job-123")

    assert plans == [first, second]


def test_plan_repository_rejects_missing_plan(tmp_path: Path) -> None:
    repository = SqlitePlanRepository(tmp_path / "plans.sqlite3")

    with pytest.raises(
        PlanNotFoundError,
        match="Plan 'missing-plan' was not found.",
    ):
        repository.get("missing-plan")


def test_plan_repository_transition(tmp_path: Path) -> None:
    database_path = tmp_path / "plans.sqlite3"
    repository = SqlitePlanRepository(database_path)

    plan = make_plan()
    repository.create(plan)

    updated_at = datetime.now(timezone.utc)

    transitioned = repository.transition(
        plan,
        PlanStatus.READY,
        updated_at,
    )

    assert transitioned.id == plan.id
    assert transitioned.job_id == plan.job_id
    assert transitioned.objective == plan.objective
    assert transitioned.status is PlanStatus.READY
    assert transitioned.created_at == plan.created_at
    assert transitioned.updated_at == updated_at
    assert transitioned.version == 2

    persisted = repository.get(plan.id)

    assert persisted == transitioned


def test_plan_repository_rejects_stale_transition(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "plans.sqlite3"
    repository = SqlitePlanRepository(database_path)

    plan = make_plan()
    repository.create(plan)

    updated_at = datetime.now(timezone.utc)

    transitioned = repository.transition(
        plan,
        PlanStatus.READY,
        updated_at,
    )

    assert transitioned.version == 2

    stale_plan = plan

    with pytest.raises(
        PlanConcurrencyError,
        match="Plan 'plan-123' changed before the transition could be persisted.",
    ):
        repository.transition(
            stale_plan,
            PlanStatus.READY,
            datetime.now(timezone.utc),
        )


def test_plan_survives_repository_recreation(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "plans.sqlite3"

    repository = SqlitePlanRepository(database_path)

    plan = make_plan()
    repository.create(plan)

    del repository

    second_repository = SqlitePlanRepository(database_path)

    retrieved = second_repository.get(plan.id)

    assert retrieved == plan
    assert retrieved.created_at.tzinfo is not None
    assert retrieved.updated_at.tzinfo is not None