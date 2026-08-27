"""Durable Frontier backed Workflow Worker。

将现有唯一 WorkflowExecution Runtime 接到 Durable Frontier，而不复制 Runtime 状态机。
Frontier 是 Worker 的 durable work item；WorkflowExecution 仍是实际 Runtime execution identity。
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update

from app.infrastructure.db import SessionLocal
from app.models.workflow_execution import WorkflowExecution, WorkflowFrontier
from app.services.workflow.frontier_lease_repository import renew_owned_frontier_lease
from app.services.workflow.frontier_repository import claim_next_frontier, transition_owned_frontier
from app.services.workflow_worker.lease_runtime import LeaseAwareWorkflowWorker


class DurableFrontierWorkflowWorker(LeaseAwareWorkflowWorker):
    """以 Durable Frontier 为调度入口，同时复用既有 Execution Runtime。"""

    async def claim_one_frontier(self, now: datetime | None = None) -> WorkflowFrontier | None:
        """Claim 一个 Durable Frontier，并在同一事务内取得对应 Execution ownership。"""
        now = now or datetime.now(UTC)
        lease_expires_at = now + timedelta(seconds=self.lease_seconds)
        async with SessionLocal() as db:
            frontier = await claim_next_frontier(
                db,
                tenant_id=await self._frontier_tenant_candidate(db),
                worker_owner=self.owner,
                lease_expires_at=lease_expires_at,
                now=now,
            )
            if frontier is None:
                await db.rollback()
                return None
            execution = (
                await db.execute(
                    select(WorkflowExecution).where(
                        WorkflowExecution.id == frontier.execution_id,
                        WorkflowExecution.tenant_id == frontier.tenant_id,
                        WorkflowExecution.status == "pending",
                        (WorkflowExecution.worker_owner.is_(None) | (WorkflowExecution.worker_lease_expires_at <= now.replace(tzinfo=None))),
                    ).with_for_update()
                )
            ).scalar_one_or_none()
            if execution is None:
                await db.rollback()
                return None
            execution.worker_owner = self.owner
            execution.worker_lease_expires_at = lease_expires_at.replace(tzinfo=None)
            execution.worker_attempt = int(execution.worker_attempt or 0) + 1
            frontier.status = "running"
            await db.commit()
            return frontier

    async def _frontier_tenant_candidate(self, db) -> UUID:
        """获取当前 Worker 可见的最早租户 Frontier；实际 claim 仍由 tenant scope 限制。"""
        result = await db.execute(
            select(WorkflowFrontier.tenant_id)
            .where(
                WorkflowFrontier.status.in_(("pending", "retry_wait")),
                WorkflowFrontier.available_at <= datetime.now(UTC).replace(tzinfo=None),
            )
            .order_by(WorkflowFrontier.available_at, WorkflowFrontier.created_at, WorkflowFrontier.id)
            .limit(1)
        )
        tenant_id = result.scalar_one_or_none()
        if tenant_id is None:
            raise LookupError("no schedulable durable frontier")
        return tenant_id

    async def _renew_frontier_forever(self, frontier_id: UUID, attempt: int) -> None:
        """持续刷新 Frontier lease；fencing 失效后停止。"""
        interval = max(0.1, self.lease_seconds / 3)
        while True:
            now = datetime.now(UTC).replace(tzinfo=None)
            async with SessionLocal() as db:
                owned = await renew_owned_frontier_lease(
                    db,
                    frontier_id=frontier_id,
                    worker_owner=self.owner,
                    attempt=attempt,
                    lease_expires_at=now + timedelta(seconds=self.lease_seconds),
                    now=now,
                )
                if not owned:
                    await db.rollback()
                    return
                await db.commit()
            await asyncio.sleep(interval)

    async def execute_frontier(self, frontier: WorkflowFrontier) -> None:
        """执行 Frontier 对应 Execution，并将 Frontier 终态与 Execution 结果收敛。"""
        heartbeat = asyncio.create_task(self._renew_frontier_forever(frontier.id, frontier.attempt))
        try:
            await super().execute_claimed(frontier.execution_id)
        finally:
            heartbeat.cancel()
            try:
                await heartbeat
            except asyncio.CancelledError:
                pass
            async with SessionLocal() as db:
                execution = (
                    await db.execute(
                        select(WorkflowExecution).where(
                            WorkflowExecution.id == frontier.execution_id,
                            WorkflowExecution.tenant_id == frontier.tenant_id,
                        )
                    )
                ).scalar_one_or_none()
                if execution is None:
                    await db.rollback()
                    return
                target = "completed" if execution.status == "completed" else "failed" if execution.status in {"failed", "cancelled"} else None
                if target is None:
                    await db.rollback()
                    return
                try:
                    await transition_owned_frontier(
                        db,
                        frontier_id=frontier.id,
                        worker_owner=self.owner,
                        attempt=frontier.attempt,
                        target_status=target,
                        now=datetime.now(UTC).replace(tzinfo=None),
                    )
                    await db.commit()
                except ValueError:
                    await db.rollback()

    async def dispatch_frontiers_once(self) -> int:
        """批量消费 Durable Frontier；异常由单个 frontier 隔离。"""
        tasks: list[asyncio.Task[None]] = []
        for _ in range(self.concurrency):
            try:
                frontier = await self.claim_one_frontier()
            except LookupError:
                break
            if frontier is None:
                break
            tasks.append(asyncio.create_task(self.execute_frontier(frontier)))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        return len(tasks)
