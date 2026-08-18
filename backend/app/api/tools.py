from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims, require_roles
from app.dependencies.db import get_db
from app.models.core import AgentTool, AuditLog, Tool
from app.services.observability_service import ObservabilityService
from app.services.tool_audit import AuditLogAdapter
from app.services.tool_observability import ToolObservabilityAdapter
from app.services.tool_rbac import ToolRBACService
from app.services.tool_repository import SqlAlchemyAuditRepository, SqlAlchemyToolRepository
from app.services.tool_runtime_service import ToolExecutionContext, ToolRuntimeService

router = APIRouter()


class ToolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    endpoint: str | None = None
    enabled: bool = True
    input_schema: dict = Field(default_factory=dict)


class ToolExecuteRequest(BaseModel):
    agent_id: UUID
    arguments: dict = Field(default_factory=dict)


@router.post("")
async def create_tool(p: ToolCreate, claims=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    tool = Tool(**p.model_dump())
    db.add(tool)
    await db.commit()
    await db.refresh(tool)
    return tool


@router.get("")
async def list_tools(claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tool).where(Tool.enabled.is_(True)).order_by(Tool.name))
    return list(result.scalars().all())


@router.post("/{tool_id}/enable")
async def enable_tool(tool_id: UUID, claims=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    tool = (await db.execute(select(Tool).where(Tool.id == tool_id))).scalar_one_or_none()
    if not tool:
        raise HTTPException(404, "Tool 不存在")
    tool.enabled = True
    await db.commit()
    return {"id": tool.id, "enabled": True}


@router.post("/{tool_id}/execute")
async def execute_tool(
    tool_id: UUID,
    payload: ToolExecuteRequest,
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    actor_id = UUID(claims["sub"])
    request_id, trace_id = ObservabilityService.new_ids()
    tool_repo = SqlAlchemyToolRepository(db, Tool, AgentTool)
    permission = ToolRBACService(db)
    audit = AuditLogAdapter(SqlAlchemyAuditRepository(db, AuditLog))
    observability = ToolObservabilityAdapter(db)
    runtime = ToolRuntimeService(tool_repo, permission.can_execute, audit, observability)
    execution = await ObservabilityService(db).start_execution(
        request_id=request_id,
        trace_id=trace_id,
        session_id=None,
        agent_id=payload.agent_id,
        agent_version=None,
        model_id=None,
    )
    await db.commit()
    context = ToolExecutionContext(actor_id, payload.agent_id, tool_id, execution.id, trace_id, request_id)
    try:
        result = await runtime.execute(context, payload.arguments)
        await ObservabilityService(db).finish_execution(execution)
        await db.commit()
        return {"execution_id": str(execution.id), "request_id": request_id, "trace_id": trace_id, "result": result}
    except Exception as exc:
        await ObservabilityService(db).finish_execution(
            execution,
            status="failed",
            error_code=getattr(exc, "code", type(exc).__name__),
            error_message="Tool execution failed",
        )
        await db.commit()
        code = getattr(exc, "code", None)
        if code == "PERMISSION_DENIED":
            raise HTTPException(403, "Tool permission denied") from exc
        if code in {"TOOL_NOT_FOUND", "TOOL_NOT_BOUND", "TOOL_DISABLED"}:
            raise HTTPException(404, str(exc)) from exc
        raise HTTPException(502, "Tool execution failed") from exc
