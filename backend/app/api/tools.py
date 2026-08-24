"""Tool API 路由。

职责：负责 Tool 管理、Agent 绑定和 Tool 执行 HTTP 协议适配，并把业务治理交给 Tool 领域服务。
边界：不直接实现 Tool 权限、审计、可观测性或执行策略；数据库访问通过领域适配器完成。
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims, require_roles
from app.dependencies.db import get_db
from app.models.core import AgentTool, AuditLog, Tool
from app.services.observability import ObservabilityService
from app.services.tool import (
    AuditLogAdapter,
    SqlAlchemyAuditRepository,
    SqlAlchemyToolRepository,
    ToolExecutionContext,
    ToolObservabilityAdapter,
    ToolRBACService,
    ToolRuntimeService,
)

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
    """List enabled tools for users and all tools for administrators.

    Administrators must be able to see disabled tools; otherwise a disabled
    tool disappears from the management UI and can never be re-enabled.
    """
    query = select(Tool).order_by(Tool.name)
    if "admin" not in claims.get("roles", []):
        query = query.where(Tool.enabled.is_(True))
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/{tool_id}/enable")
async def enable_tool(tool_id: UUID, claims=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    tool = (await db.execute(select(Tool).where(Tool.id == tool_id))).scalar_one_or_none()
    if not tool:
        raise HTTPException(404, "Tool 不存在")
    tool.enabled = True
    await db.commit()
    return {"id": tool.id, "enabled": True}


@router.post("/{tool_id}/disable")
async def disable_tool(tool_id: UUID, claims=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    tool = (await db.execute(select(Tool).where(Tool.id == tool_id))).scalar_one_or_none()
    if not tool:
        raise HTTPException(404, "Tool 不存在")
    tool.enabled = False
    await db.commit()
    return {"id": tool.id, "enabled": False}


@router.post("/{tool_id}/bind/{agent_id}")
async def bind_tool(
    tool_id: UUID,
    agent_id: UUID,
    claims=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    tool = (await db.execute(select(Tool).where(Tool.id == tool_id))).scalar_one_or_none()
    if not tool:
        raise HTTPException(404, "Tool 不存在")
    agent_exists = (await db.execute(select(AgentTool.agent_id).where(AgentTool.agent_id == agent_id).limit(1))).scalar_one_or_none()
    if agent_exists is None:
        from app.models.core import Agent

        agent = (await db.execute(select(Agent.id).where(Agent.id == agent_id))).scalar_one_or_none()
        if agent is None:
            raise HTTPException(404, "Agent 不存在")
    binding = (await db.execute(
        select(AgentTool).where(AgentTool.agent_id == agent_id, AgentTool.tool_id == tool_id)
    )).scalar_one_or_none()
    if binding is None:
        binding = AgentTool(agent_id=agent_id, tool_id=tool_id, enabled=True)
        db.add(binding)
    else:
        binding.enabled = True
    await db.commit()
    return {"agent_id": agent_id, "tool_id": tool_id, "enabled": True}


@router.delete("/{tool_id}/bind/{agent_id}")
async def unbind_tool(
    tool_id: UUID,
    agent_id: UUID,
    claims=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    binding = (await db.execute(
        select(AgentTool).where(AgentTool.agent_id == agent_id, AgentTool.tool_id == tool_id)
    )).scalar_one_or_none()
    if binding is None:
        raise HTTPException(404, "Tool 绑定不存在")
    await db.delete(binding)
    await db.commit()
    return {"agent_id": agent_id, "tool_id": tool_id, "enabled": False}


@router.post("/{tool_id}/execute")
async def execute_tool(
    tool_id: UUID,
    payload: ToolExecuteRequest,
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    actor_id = UUID(str(claims["sub"]))
    request_id, trace_id = ObservabilityService.new_ids()
    tool_repo = SqlAlchemyToolRepository(db, Tool, AgentTool)
    permission = ToolRBACService(db)
    audit = AuditLogAdapter(SqlAlchemyAuditRepository(db, AuditLog))
    observability = ToolObservabilityAdapter(db)
    runtime = ToolRuntimeService(
        tool_repo,
        tool_repo,
        permission.can_execute,
        audit_logger=audit,
        observability=observability,
    )
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
