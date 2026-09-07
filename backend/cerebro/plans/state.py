from __future__ import annotations

from cerebro.plans.models import PlanStatus


class InvalidPlanTransitionError(ValueError):
    def __init__(self, current: PlanStatus, target: PlanStatus) -> None:
        super().__init__(
            f"Cannot transition a plan from {current.value} to {target.value}."
        )
        self.current = current
        self.target = target


ALLOWED_TRANSITIONS: dict[PlanStatus, frozenset[PlanStatus]] = {
    PlanStatus.DRAFT: frozenset({PlanStatus.READY}),
    PlanStatus.READY: frozenset(),
}


def validate_transition(
    current: PlanStatus,
    target: PlanStatus,
) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidPlanTransitionError(current, target)
