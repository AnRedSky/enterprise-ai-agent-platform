from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow, WorkflowVersion
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution
from app.runtime.workflow_runtime import WorkflowRuntime


class WorkflowExecutionService:
    EXECUTION_STATES = {"pending", "running", "completed", "failed", "cancelled"}
    NODE_STATES = {"pending", "running", "completed", "failed", "skipped"}
    TERMINAL_EXECUTION_STATES = {"completed", "failed", "cancelled"}

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, workflow: Workflow, version: WorkflowVersion, actor_id: UUID, input_data: dict) -> WorkflowExecution:
        if workflow.published_version_id != version.id or version.status != "published":
            raise HTTPException(409, "只能执行当前已发布版本")
        WorkflowRuntime.validate_definition(version.definition)
        execution = WorkflowExecution(
            tenant_id=workflow.tenant_id,
            workflow_id=workflow.id,
            workflow_version_id=version.id,
            created_by=actor_id,
            status="pending",
            input_data=input_data,
        )
        self.db.add(execution)
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def get(self, execution_id: UUID, tenant_id: UUID, actor_id: UUID, admin: bool = False) -> WorkflowExecution:
        query = select(WorkflowExecution).where(WorkflowExecution.id == execution_id, WorkflowExecution.tenant_id == tenant_id)
        if not admin:
            query = query.where(WorkflowExecution.created_by == actor_id)
        execution = (await self.db.execute(query)).scalar_one_or_none()
        if execution is None:
            raise HTTPException(404, "Workflow Execution 不存在")
        return execution

    async def nodes(self, execution: WorkflowExecution) -> list[WorkflowNodeExecution]:
        result = await self.db.execute(
            select(WorkflowNodeExecution)
            .where(WorkflowNodeExecution.execution_id == execution.id)
            .order_by(WorkflowNodeExecution.created_at.asc(), WorkflowNodeExecution.id.asc())
        )
        return list(result.scalars().all())

    async def transition(self, execution: WorkflowExecution, target_status: str, node_id: str | None = None,
                         error_code: str | None = None, error_message: str | None = None,
                         output_data: dict | None = None) -> WorkflowExecution:
        if target_status not in self.EXECUTION_STATES:
            raise HTTPException(400, "不支持的 Execution 状态")
        current = execution.status
        allowed = {"pending": {"running", "cancelled"}, "running": {"completed", "failed", "cancelled"},
                   "completed": set(), "failed": set(), "cancelled": set()}
        if target_status not in allowed[current]:
            raise HTTPException(409, f"Execution 不允许从 {current} 转换到 {target_status}")
        now = datetime.now(UTC).replace(tzinfo=None)
        execution.status = target_status
        if node_id is not None:
            execution.current_node_id = node_id
        if output_data is not None:
            execution.output_data = output_data
        if error_code is not None:
            execution.error_code = error_code
        if error_message is not None:
            execution.error_message = error_message
        if target_status == "running" and execution.started_at is None:
            execution.started_at = now
        if target_status in self.TERMINAL_EXECUTION_STATES:
            execution.ended_at = now
            execution.current_node_id = None
        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def transition_node(self, execution: WorkflowExecution, node_id: str, target_status: str,
                              input_data: dict | None = None, output_data: dict | None = None,
                              error_code: str | None = None, error_message: str | None = None) -> WorkflowNodeExecution:
        if target_status not in self.NODE_STATES:
            raise HTTPException(400, "不支持的 Node Execution 状态")
        if execution.status in self.TERMINAL_EXECUTION_STATES:
            raise HTTPException(409, "已结束 Execution 不允许继续推进节点")
        node = (await self.db.execute(select(WorkflowNodeExecution).where(
            WorkflowNodeExecution.execution_id == execution.id, WorkflowNodeExecution.node_id == node_id
        ))).scalar_one_or_none()
        if node is None:
            node = WorkflowNodeExecution(execution_id=execution.id, node_id=node_id)
            self.db.add(node)
            await self.db.flush()
        allowed = {"pending": {"running", "skipped"}, "running": {"completed", "failed", "skipped"},
                   "completed": set(), "failed": set(), "skipped": set()}
        if target_status not in allowed[node.status]:
            raise HTTPException(409, f"Node 不允许从 {node.status} 转换到 {target_status}")
        now = datetime.now(UTC).replace(tzinfo=None)
        node.status = target_status
        if input_data is not None:
            node.input_data = input_data
        if output_data is not None:
            node.output_data = output_data
        if error_code is not None:
            node.error_code = error_code
        if error_message is not None:
            node.error_message = error_message
        if target_status == "running" and node.started_at is None:
            node.started_at = now
            execution.current_node_id = node_id
        if target_status in {"completed", "failed", "skipped"}:
            node.ended_at = now
        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def run(self, execution: WorkflowExecution, version: WorkflowVersion, actor_id: UUID,
                  is_admin: bool = False) -> WorkflowExecution:
        nodes = WorkflowRuntime.validate_definition(version.definition)
        if execution.status != "pending":
            raise HTTPException(409, "只有 pending Execution 可以启动 Runtime")
        runtime = WorkflowRuntime(self.db)
        data = dict(execution.input_data or {})
        try:
            await self.transition(execution, "running")
            for node in nodes:
                node_id = node["id"]
                await self.transition_node(execution, node_id, "running", input_data=data)
                try:
                    data = await runtime.execute_node(node, data, actor_id, is_admin, execution.id)
                except Exception as exc:
                    await self.transition_node(execution, node_id, "failed", error_code=type(exc).__name__,
                                               error_message=str(exc))
                    await self.transition(execution, "failed", error_code=type(exc).__name__,
                                           error_message="Workflow node execution failed")
                    raise
                await self.transition_node(execution, node_id, "completed", output_data=data)
            await self.transition(execution, "completed", output_data=data)
            return execution
        except HTTPException:
            raise
        except Exception as exc:
            if execution.status == "running":
                await self.transition(execution, "failed", error_code=type(exc).__name__,
                                       error_message="Workflow execution failed")
            raise
