"""Runtime Worker / Scheduler 诊断 API。

职责：将认证租户上下文适配到 RuntimeDiagnosticsService，提供只读诊断 HTTP Contract。
边界：不执行 Worker / Scheduler 操作，不接受客户端 tenant_id，不从业务活动推断进程存活。
关键依赖：FastAPI、认证 Claims、数据库依赖、RuntimeDiagnosticsService。
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import bearer, current_claims
from app.dependencies.db import get_db
from app.schemas.runtime import RuntimeSchedulerDiagnosticsResponse, RuntimeWorkerDiagnosticsResponse
from app.services.runtime_operations.diagnostics import RuntimeDiagnosticsService

router = APIRouter(prefix="/diagnostics", tags=["runtime-diagnostics"])


def _claims(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    """解析当前认证 Claims。"""
    if credentials is None:
        return current_claims()
    return current_claims(credentials)


def _tenant_id(claims: dict) -> UUID:
    """从认证上下文取得唯一租户边界。"""
    return UUID(claims["tenant_id"])


@router.get("/worker", response_model=RuntimeWorkerDiagnosticsResponse)
async def worker_diagnostics(
    window_hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=100),
    claims: dict = Depends(_claims),
    db: AsyncSession = Depends(get_db),
):
    """返回当前租户 Worker Durable claim / lease 诊断。"""
    return await RuntimeDiagnosticsService(db).worker(_tenant_id(claims), window_hours=window_hours, limit=limit)


@router.get("/scheduler", response_model=RuntimeSchedulerDiagnosticsResponse)
async def scheduler_diagnostics(
    limit: int = Query(50, ge=1, le=100),
    claims: dict = Depends(_claims),
    db: AsyncSession = Depends(get_db),
):
    """返回当前租户 Scheduler Durable posture。"""
    return await RuntimeDiagnosticsService(db).scheduler(_tenant_id(claims), limit=limit)
