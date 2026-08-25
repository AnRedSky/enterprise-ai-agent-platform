"""Worker Runtime 一致性诊断脚本。

职责：只读检查 PostgreSQL 中 Workflow Execution 与 Node Execution 的 ownership / 状态一致性。
边界：不启动、停止或修改 API、Scheduler、Worker，也不自动修复数据。
关键依赖：项目 SessionLocal、WorkflowExecution、WorkflowNodeExecution ORM。
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

# 该脚本位于 backend/scripts/dev；直接执行时 Python 默认只把脚本目录加入 sys.path。
# 将 backend 根目录显式加入路径，保证 `uv run python .\scripts\dev\...py` 与
# `python -m ...` 一样能够解析正式 app 包入口，避免把工作目录偶然性当成运行前提。
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.infrastructure.db import SessionLocal
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution


async def inspect_consistency() -> int:
    """检查 Worker 运行时可能导致重复 Runtime 的持久化异常。

    Returns:
        0 表示未发现一致性异常；2 表示发现需要人工处理的异常。

    事务边界：仅执行只读查询，不提交任何修改；发现异常后必须人工结合 Worker 日志判断，
    当前阶段禁止脚本自动 resume 或重置 running Node。
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    async with SessionLocal() as db:
        pending_with_running = list(
            (
                await db.execute(
                    select(WorkflowExecution, WorkflowNodeExecution)
                    .join(
                        WorkflowNodeExecution,
                        WorkflowNodeExecution.execution_id == WorkflowExecution.id,
                    )
                    .where(
                        WorkflowExecution.status == "pending",
                        WorkflowNodeExecution.status == "running",
                    )
                    .order_by(WorkflowExecution.created_at.asc())
                )
            ).all()
        )
        expired_running_owners = list(
            (
                await db.execute(
                    select(WorkflowExecution)
                    .where(
                        WorkflowExecution.status == "running",
                        WorkflowExecution.worker_owner.is_not(None),
                        WorkflowExecution.worker_lease_expires_at.is_not(None),
                        WorkflowExecution.worker_lease_expires_at < now,
                    )
                    .order_by(WorkflowExecution.created_at.asc())
                )
            ).scalars().all()
        )

    print("============================================================")
    print("Enterprise AI Agent Platform - Worker Runtime Consistency")
    print("============================================================")
    print(f"[INFO] Checked at: {now.isoformat()} UTC")
    print(f"[INFO] Pending Execution with running Node: {len(pending_with_running)}")
    for execution, node in pending_with_running:
        print(
            "[ERROR] pending/running invariant: "
            f"execution={execution.id} worker_owner={execution.worker_owner!r} "
            f"node={node.node_id} attempt={node.attempt}"
        )
    print(f"[INFO] Running Execution with expired Worker lease: {len(expired_running_owners)}")
    for execution in expired_running_owners:
        print(
            "[WARN] expired running lease candidate: "
            f"execution={execution.id} worker_owner={execution.worker_owner!r} "
            f"lease_expires_at={execution.worker_lease_expires_at!s}"
        )

    if pending_with_running:
        print("[FAIL] Persistent state is inconsistent; do not resume these executions automatically.")
        return 2
    print("[PASS] No pending Execution contains a running Node.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(inspect_consistency()))
