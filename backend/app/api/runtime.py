"""Runtime 查询 API 路由模块。

模块职责：提供执行记录、事件时间线、工作流 Trace 与审计日志的 HTTP 查询接口。
边界：仅负责协议参数、身份与租户上下文适配；查询业务规则统一由 RuntimeQueryService / WorkflowExecutionService 承担。
关键依赖：FastAPI、SQLAlchemy AsyncSession，以及 canonical `app.dependencies.db.get_db` 数据库依赖。
"""

from datetime import datetime, UTC
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.core.auth import bearer, current_claims
from app.models.execution import Execution
from app.schemas.runtime import AuditLogListResponse, ExecutionListResponse, ExecutionTimelineResponse, WorkflowTraceResponse
from app.services.runtime_query import RuntimeQueryService
from app.services.workflow import WorkflowExecutionService

router = APIRouter(prefix="/api/v1/runtime", tags=["runtime"])


def _runtime_claims(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if credentials is None:
        return current_claims()
    return current_claims(credentials)


def _identity(claims: dict | None = None):
    if claims is None:
        claims = current_claims()
    actor_id = UUID(claims["sub"])
    tenant_id = UUID(claims["tenant_id"])
    admin = "admin" in claims.get("roles", [])
    return actor_id, tenant_id, admin
