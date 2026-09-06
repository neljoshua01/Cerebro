from __future__ import annotations

from cerebro.tasks.models import TaskStatus


class InvalidTaskTransitionError(ValueError):
    def __init__(self, current: TaskStatus, target: TaskStatus) -> None:
        super().__init__(
            f"Cannot transition a task from {current.value} to {target.value}."
        )
        self.current = current
        self.target = target


ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PENDING: frozenset(
        {TaskStatus.READY, TaskStatus.CANCELLED}
    ),
    TaskStatus.READY: frozenset(
        {TaskStatus.RUNNING, TaskStatus.CANCELLED}
    ),
    TaskStatus.RUNNING: frozenset(
        {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }
    ),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.FAILED: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}


def validate_transition(
    current: TaskStatus,
    target: TaskStatus,
) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTaskTransitionError(current, target)
