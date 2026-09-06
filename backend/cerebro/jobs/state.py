from __future__ import annotations

from cerebro.jobs.models import JobStatus


class InvalidJobTransitionError(ValueError):
    def __init__(self, current: JobStatus, target: JobStatus) -> None:
        super().__init__(f"Cannot transition a job from {current.value} to {target.value}.")
        self.current = current
        self.target = target


# Phase 1A deliberately stops at WAITING_FOR_APPROVAL. Moving a job from that
# state to EXECUTING will be performed by the Phase 2 approval capability, not
# by an unrestricted lifecycle endpoint.
ALLOWED_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.CREATED: frozenset({JobStatus.UNDERSTANDING, JobStatus.CANCELLED}),
    JobStatus.UNDERSTANDING: frozenset({JobStatus.PLANNING, JobStatus.FAILED, JobStatus.CANCELLED}),
    JobStatus.PLANNING: frozenset({JobStatus.PLAN_READY, JobStatus.FAILED, JobStatus.CANCELLED}),
    JobStatus.PLAN_READY: frozenset({JobStatus.WAITING_FOR_APPROVAL, JobStatus.FAILED, JobStatus.CANCELLED}),
    JobStatus.WAITING_FOR_APPROVAL: frozenset({JobStatus.CANCELLED}),
    JobStatus.EXECUTING: frozenset({JobStatus.OBSERVING, JobStatus.FAILED, JobStatus.CANCELLED}),
    JobStatus.OBSERVING: frozenset({JobStatus.EVALUATING, JobStatus.FAILED, JobStatus.CANCELLED}),
    JobStatus.EVALUATING: frozenset({JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}),
    JobStatus.COMPLETED: frozenset(),
    JobStatus.FAILED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
}


def validate_transition(current: JobStatus, target: JobStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidJobTransitionError(current, target)
