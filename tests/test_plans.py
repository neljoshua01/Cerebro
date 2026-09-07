from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from cerebro.plans.models import Plan, PlanStatus
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
