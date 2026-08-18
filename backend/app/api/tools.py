from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import current_claims, require_roles
from app.dependencies.db import get_db
from app.models.core import Tool

router = APIRouter()
class ToolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    endpoint: str | None = None
    enabled: bool = True

@router.post("")
async def create_tool(p: ToolCreate, claims=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    tool = Tool(**p.model_dump()); db.add(tool); await db.commit(); await db.refresh(tool)
    return tool

@router.get("")
async def list_tools(claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tool).where(Tool.enabled == True).order_by(Tool.name))
    return list(result.scalars().all())

@router.post("/{tool_id}/enable")
async def enable_tool(tool_id: UUID, claims=Depends(require_roles("admin")), db: AsyncSession = Depends(get_db)):
    tool = (await db.execute(select(Tool).where(Tool.id == tool_id))).scalar_one_or_none()
    if not tool: from fastapi import HTTPException; raise HTTPException(404, "Tool 不存在")
    tool.enabled = True; await db.commit(); return {"id":tool.id,"enabled":True}
