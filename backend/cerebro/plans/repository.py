from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Protocol

from cerebro.plans.models import Plan, PlanStatus


class PlanRepository(Protocol):
    def create(self, plan: Plan) -> Plan:
        ...

    def get(self, plan_id: str) -> Plan:
        ...

    def list_for_job(self, job_id: str) -> list[Plan]:
        ...

    def transition(
        self,
        plan: Plan,
        target: PlanStatus,
        updated_at: datetime,
    ) -> Plan:
        ...


class PlanNotFoundError(LookupError):
    def __init__(self, plan_id: str) -> None:
        super().__init__(f"Plan '{plan_id}' was not found.")
        self.plan_id = plan_id


class PlanConcurrencyError(RuntimeError):
    """Raised when a concurrent update changed a plan before this update."""


class SqlitePlanRepository:
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
                CREATE TABLE IF NOT EXISTS plans (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    version INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_plans_job_created_at "
                "ON plans(job_id, created_at, id)"
            )

    def create(self, plan: Plan) -> Plan:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO plans (
                    id,
                    job_id,
                    objective,
                    status,
                    created_at,
                    updated_at,
                    version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.id,
                    plan.job_id,
                    plan.objective,
                    plan.status.value,
                    _serialize_timestamp(plan.created_at),
                    _serialize_timestamp(plan.updated_at),
                    plan.version,
                ),
            )

        return plan

    def get(self, plan_id: str) -> Plan:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM plans WHERE id = ?",
                (plan_id,),
            ).fetchone()

        if row is None:
            raise PlanNotFoundError(plan_id)

        return _to_plan(row)

    def list_for_job(self, job_id: str) -> list[Plan]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM plans
                WHERE job_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (job_id,),
            ).fetchall()

        return [_to_plan(row) for row in rows]

    def transition(
        self,
        plan: Plan,
        target: PlanStatus,
        updated_at: datetime,
    ) -> Plan:
        new_version = plan.version + 1

        with self._connect() as connection:
            result = connection.execute(
                """
                UPDATE plans
                SET status = ?, updated_at = ?, version = ?
                WHERE id = ?
                  AND version = ?
                  AND status = ?
                """,
                (
                    target.value,
                    _serialize_timestamp(updated_at),
                    new_version,
                    plan.id,
                    plan.version,
                    plan.status.value,
                ),
            )

        if result.rowcount != 1:
            raise PlanConcurrencyError(
                f"Plan '{plan.id}' changed before the transition could be persisted."
            )

        return Plan(
            id=plan.id,
            job_id=plan.job_id,
            objective=plan.objective,
            status=target,
            created_at=plan.created_at,
            updated_at=updated_at,
            version=new_version,
        )


def _serialize_timestamp(value: datetime) -> str:
    return value.isoformat()


def _to_plan(row: sqlite3.Row) -> Plan:
    return Plan(
        id=row["id"],
        job_id=row["job_id"],
        objective=row["objective"],
        status=PlanStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        version=row["version"],
    )