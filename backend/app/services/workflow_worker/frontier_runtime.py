"""Durable Frontier backed Workflow Worker。

职责：将现有唯一 WorkflowExecution Runtime 接到 Durable Frontier，而不复制 Runtime 状态机。
边界：Frontier 是 Worker 的 durable work item；WorkflowExecution 仍是实际 Runtime execution identity。
关键依赖：PostgreSQL、WorkflowFrontier repository、WorkflowExecution ownership 与 LeaseAwareWorkflowWorker。
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select

from app.infrastructure.db import SessionLocal
from app.models.workflow_execution import WorkflowExecution, WorkflowFrontier
from app.services.workflow.frontier_lease_repository import renew_owned_frontier_lease
from app.services.workflow.frontier_repository import claim_next_frontier, transition_owned_frontier
from app.services.workflow.governance import WorkflowGovernanceService
from app.services.workflow_worker.lease_runtime import LeaseAwareWorkflowWorker
from app.services.workflow_worker.runtime_entry import execute_claimed_execution


class DurableFrontierWorkflowWorker(LeaseAwareWorkflowWorker):
    """以 Durable Frontier 为调度入口，同时复用既有 Execution Runtime。"""

    async def claim_one_frontier(self, now: datetime | None = None) -> WorkflowFrontier | None:
        """Claim 一个 Durable Frontier，并安全取得对应 Execution ownership。"""
        now = now or datetime.now(UTC)
        lease_expires_at = now + timedelta(seconds=self.lease_seconds)
        now_naive = now.replace(tzinfo=None)
        async with SessionLocal() as db:
            try:
                tenant_id = await self._frontier_tenant_candidate(db, now)
            except LookupError:
                await db.rollback()
                return None
            frontier = await claim_next_frontier(
                db,
                tenant_id=tenant_id,
                worker_owner=self.owner,
                lease_expires_at=lease_expires_at,
                now=now,
            )
            if frontier is None:
                await db.rollback()
                return None
            execution = (
                await db.execute(
                    select(WorkflowExecution)
                    .where(
                        WorkflowExecution.id == frontier.execution_id,
                        WorkflowExecution.tenant_id == frontier.tenant_id,
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if execution is None:
                await db.rollback()
                return None
            execution_lease_expired = (
                execution.worker_lease_expires_at is None
                or execution.worker_lease_expires_at <= now_naive
            )
            owned_by_current_worker = execution.worker_owner == self.owner
            if execution.status == "pending" and (execution.worker_owner is None or execution_lease_expired):
                execution.worker_owner = self.owner
                execution.worker_lease_expires_at = lease_expires_at.replace(tzinfo=None)
                execution.worker_attempt = int(execution.worker_attempt or 0) + 1
            elif execution.status == "pending" and owned_by_current_worker:
                execution.worker_lease_expires_at = lease_expires_at.replace(tzinfo=None)
            elif execution.status == "running" and owned_by_current_worker:
                execution.worker_lease_expires_at = lease_expires_at.replace(tzinfo=None)
            elif execution.status == "running" and execution_lease_expired:
                execution.status = "pending"
                execution.current_node_id = None
                execution.worker_owner = self.owner
                execution.worker_lease_expires_at = lease_expires_at.replace(tzinfo=None)
                execution.worker_attempt = int(execution.worker_attempt or 0) + 1
            else:
                await db.rollback()
                return None
            if execution.status == "pending":
                execution.status = "running"
                if execution.started_at is None:
                    execution.started_at = now_naive
                await WorkflowGovernanceService(db).trace(
                    execution,
                    execution.created_by,
                    "execution.state_changed",
                    "running",
                    data={"from": "pending", "to": "running", "worker_attempt": int(execution.worker_attempt or 0)},
                )
            frontier.status = "running"
            await db.commit()
            return frontier

    async def _frontier_tenant_candidate(self, db, now: datetime) -> UUID:
        """获取最早且当前 Worker 真正可领取的 Frontier 所属租户。"""
        now_naive = now.replace(tzinfo=None)
        execution_available = or_(
            and_(
                WorkflowExecution.status == "pending",
                or_(
                    WorkflowExecution.worker_owner.is_(None),
                    WorkflowExecution.worker_lease_expires_at.is_(None),
                    WorkflowExecution.worker_lease_expires_at <= now_naive,
                    WorkflowExecution.worker_owner == self.owner,
                ),
            ),
            and_(
                WorkflowExecution.status == "running",
                or_(
                    WorkflowExecution.worker_owner == self.owner,
                    WorkflowExecution.worker_lease_expires_at.is_(None),
                    WorkflowExecution.worker_lease_expires_at <= now_naive,
                ),
            ),
        )
        result = await db.execute(
            select(WorkflowFrontier.tenant_id)
            .join(
                WorkflowExecution,
                and_(
                    WorkflowExecution.id == WorkflowFrontier.execution_id,
                    WorkflowExecution.tenant_id == WorkflowFrontier.tenant_id,
                ),
            )
            .where(
                WorkflowFrontier.status.in_(("pending", "retry_wait")),
                WorkflowFrontier.available_at <= now_naive,
                execution_available,
            )
            .order_by(WorkflowFrontier.available_at, WorkflowFrontier.created_at, WorkflowFrontier.id)
            .limit(1)
        )
        tenant_id = result.scalar_one_or_none()
        if tenant_id is None:
            raise LookupError("no safely schedulable durable frontier")
        return tenant_id

    async def _renew_frontier_forever(
        self,
        frontier_id: UUID,
        attempt: int,
        runtime_task: asyncio.Task[object] | None = None,
    ) -> None:
        """持续刷新 Frontier/Execution lease；明确失去 ownership 时主动取消 Runtime。"""
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
                    if runtime_task is not None and not runtime_task.done():
                        runtime_task.cancel()
                    return
                await db.commit()
            await asyncio.sleep(interval)

    async def execute_frontier(self, frontier: WorkflowFrontier) -> None:
        """执行 Frontier 对应 Execution，并将 Frontier 终态与 Execution 结果收敛。"""
        runtime_task = asyncio.current_task()
        heartbeat = asyncio.create_task(
            self._renew_frontier_forever(frontier.id, frontier.attempt, runtime_task)
        )
        try:
            await execute_claimed_execution(self, frontier.execution_id)
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

    async def dispatch_once(self) -> int:
        """批量消费 Durable Frontier；Frontier 是默认 Worker 的唯一调度入口。"""
        tasks: list[asyncio.Task[None]] = []
        for _ in range(self.concurrency):
            frontier = await self.claim_one_frontier()
            if frontier is None:
                break
            tasks.append(asyncio.create_task(self.execute_frontier(frontier)))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        return len(tasks)

    async def dispatch_frontiers_once(self) -> int:
        """显式命名的 Frontier dispatch API，供调度器与单元测试使用。"""
        return await self.dispatch_once()
