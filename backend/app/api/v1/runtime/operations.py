"""Runtime 运维聚合 API 路由。"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import bearer, current_claims
from app.dependencies.db import get_db
from app.services.integration.webhook_delivery_repository import WebhookDeliveryRepository
from app.services.runtime_operations import RuntimeOperationsEnterpriseService, RuntimeOperationsService, RuntimeProviderHealthService
from app.services.runtime_operations.alerting import RuntimeAlertEvaluator


class RuntimeOperationsOverview(BaseModel):
    window_hours: int
    since: datetime
    generated_at: datetime
    events: dict
    deliveries: dict
    slo: dict


class DeadLetterItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    integration_event_id: UUID
    destination_id: UUID
    subscription_id: UUID
    status: str
    attempt_count: int
    next_attempt_at: datetime | None = None
    last_attempt_at: datetime | None = None
    delivered_at: datetime | None = None
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    response_status_code: int | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DeadLetterListResponse(BaseModel):
    items: list[DeadLetterItem]
    page: int
    page_size: int
    total: int


class BatchReplayRequest(BaseModel):
    delivery_ids: list[UUID]


class BatchReplayResponse(BaseModel):
    replayed: list[UUID]
    rejected: list[dict]


class ProviderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    provider_type: str = Field(min_length=1, max_length=80)
    config: dict = Field(default_factory=dict)


class ProviderEnabledRequest(BaseModel):
    enabled: bool


class AlertRuleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    metric_name: str = Field(min_length=1, max_length=120)
    operator: str
    threshold: float
    window_minutes: int = Field(default=15, ge=1, le=10080)
    severity: str = "warning"


class AlertRuleEnabledRequest(BaseModel):
    enabled: bool


router = APIRouter(prefix="/operations", tags=["runtime-operations"])


def _claims(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if credentials is None:
        return current_claims()
    return current_claims(credentials)


def _tenant_id(claims: dict) -> UUID:
    return UUID(claims["tenant_id"])


def _actor(claims: dict) -> str:
    return str(UUID(claims["sub"]))


def _require_admin(claims: dict) -> None:
    roles = claims.get("roles", [])
    if isinstance(roles, str):
        roles = [roles]
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="runtime operations management requires admin role")


@router.get("/overview", response_model=RuntimeOperationsOverview)
async def runtime_operations_overview(window_hours: int = Query(24, ge=1, le=168), claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    return await RuntimeOperationsService(db).overview(_tenant_id(claims), window_hours=window_hours)


@router.get("/dimensions")
async def runtime_operations_dimensions(window_hours: int = Query(24, ge=1, le=168), claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    return await RuntimeOperationsService(db).dimension_metrics(_tenant_id(claims), window_hours=window_hours)


@router.get("/alerts")
async def runtime_operations_alerts(window_hours: int = Query(24, ge=1, le=168), claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    return await RuntimeOperationsService(db).alerts(_tenant_id(claims), window_hours=window_hours)


@router.get("/providers")
async def list_providers(claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    return {"items": [item for item in await RuntimeOperationsEnterpriseService(db).providers(_tenant_id(claims))]}


@router.post("/providers", status_code=201)
async def create_provider(request: ProviderCreateRequest, claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    _require_admin(claims)
    try:
        item = await RuntimeOperationsEnterpriseService(db).create_provider(_tenant_id(claims), request.name, request.provider_type, request.config, _actor(claims))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await db.commit()
    return item


@router.patch("/providers/{provider_id}")
async def set_provider_enabled(provider_id: UUID, request: ProviderEnabledRequest, claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    _require_admin(claims)
    try:
        item = await RuntimeOperationsEnterpriseService(db).set_provider_enabled(_tenant_id(claims), provider_id, request.enabled, _actor(claims))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    return item


@router.post("/providers/{provider_id}/health", status_code=200)
async def probe_provider_health(provider_id: UUID, claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    _require_admin(claims)
    try:
        result = await RuntimeProviderHealthService().probe(db, _tenant_id(claims), provider_id, _actor(claims))
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await db.commit()
    return {"provider_id": result.provider_id, "status": result.status, "http_status": result.http_status, "latency_ms": result.latency_ms, "error": result.error}


@router.get("/destinations")
async def list_destinations(claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    return {"items": [item for item in await RuntimeOperationsEnterpriseService(db).destinations(_tenant_id(claims))]}


@router.get("/alert-rules")
async def list_alert_rules(claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    return {"items": [item for item in await RuntimeOperationsEnterpriseService(db).alerts_rules(_tenant_id(claims))]}


@router.post("/alert-rules", status_code=201)
async def create_alert_rule(request: AlertRuleCreateRequest, claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    _require_admin(claims)
    try:
        item = await RuntimeOperationsEnterpriseService(db).create_alert_rule(_tenant_id(claims), request.name, request.metric_name, request.operator, request.threshold, request.window_minutes, request.severity, _actor(claims))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await db.commit()
    return item


@router.patch("/alert-rules/{rule_id}")
async def set_alert_rule_enabled(rule_id: UUID, request: AlertRuleEnabledRequest, claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    _require_admin(claims)
    try:
        item = await RuntimeOperationsEnterpriseService(db).set_alert_rule_enabled(_tenant_id(claims), rule_id, request.enabled, _actor(claims))
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    return item


@router.post("/alert-rules/evaluate")
async def evaluate_alert_rules(claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    """显式执行当前租户规则评估；只返回生命周期状态发生变化的事实。"""
    _require_admin(claims)
    transitions = await RuntimeAlertEvaluator(db).evaluate(_tenant_id(claims), actor=_actor(claims))
    await db.commit()
    return {"items": transitions, "count": len(transitions)}


@router.post("/metrics/snapshot")
async def create_metrics_snapshot(claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    count = await RuntimeOperationsEnterpriseService(db).snapshot(_tenant_id(claims))
    await db.commit()
    return {"samples_written": count}


@router.get("/metrics/series")
async def metric_series(metric_name: str = Query(..., min_length=1, max_length=120), window_minutes: int = Query(60, ge=1, le=10080), dimension_key: str | None = Query(None, min_length=1, max_length=32), dimension_value: str | None = Query(None, min_length=1, max_length=255), claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    """查询租户时间序列，可按规范维度进一步过滤。"""
    try:
        rows = await RuntimeOperationsEnterpriseService(db).series(_tenant_id(claims), metric_name, window_minutes, dimension_key=dimension_key, dimension_value=dimension_value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"items": rows, "metric_name": metric_name, "window_minutes": window_minutes, "dimension_key": dimension_key, "dimension_value": dimension_value}


@router.get("/metrics/prometheus")
async def prometheus_metrics(claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    return Response(content=await RuntimeOperationsEnterpriseService(db).prometheus(_tenant_id(claims)), media_type="text/plain; version=0.0.4")


@router.get("/metrics/otlp")
async def otlp_metrics(claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    return await RuntimeOperationsEnterpriseService(db).otlp(_tenant_id(claims))


@router.get("/audit")
async def runtime_operation_audit(limit: int = Query(100, ge=1, le=1000), claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    return {"items": await RuntimeOperationsEnterpriseService(db).audit_list(_tenant_id(claims), limit)}


@router.get("/audit/query")
async def runtime_operation_audit_query(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), action: str | None = Query(None, min_length=1, max_length=80), resource_type: str | None = Query(None, min_length=1, max_length=80), resource_id: str | None = Query(None, min_length=1, max_length=128), outcome: str | None = Query(None, min_length=1, max_length=24), actor: Annotated[str | None, StringConstraints(min_length=1, max_length=128), Query(None)] = None, since: datetime | None = Query(None), until: datetime | None = Query(None), claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    """分页查询当前租户运维审计；所有过滤条件均叠加认证租户范围。"""
    try:
        result_page, result_size, total, rows = await RuntimeOperationsService(db).audit_query(_tenant_id(claims), page=page, page_size=page_size, action=action, resource_type=resource_type, resource_id=resource_id, outcome=outcome, actor=actor, since=since, until=until)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"items": rows, "page": result_page, "page_size": result_size, "total": total}


@router.get("/dead-letters", response_model=DeadLetterListResponse)
async def list_dead_letters(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    page, page_size, total, rows = await RuntimeOperationsService(db).dead_letters(_tenant_id(claims), page=page, page_size=page_size)
    return {"items": rows, "page": page, "page_size": page_size, "total": total}


@router.post("/dead-letters/replay", response_model=BatchReplayResponse)
async def batch_replay_dead_letters(request: BatchReplayRequest, claims: dict = Depends(_claims), db: AsyncSession = Depends(get_db)):
    _require_admin(claims)
    if not request.delivery_ids or len(request.delivery_ids) > 100:
        raise HTTPException(status_code=422, detail="delivery_ids must contain 1 to 100 items")
    tenant_id = _tenant_id(claims)
    actor = _actor(claims)
    replayed: list[UUID] = []
    rejected: list[dict] = []
    repository = WebhookDeliveryRepository()
    for delivery_id in dict.fromkeys(request.delivery_ids):
        try:
            record = await repository.replay(db, tenant_id, delivery_id, actor)
        except ValueError as exc:
            await db.rollback()
            rejected.append({"delivery_id": delivery_id, "reason": str(exc)})
            continue
        if record is None:
            rejected.append({"delivery_id": delivery_id, "reason": "delivery not found"})
            continue
        replayed.append(delivery_id)
    await db.commit()
    return {"replayed": replayed, "rejected": rejected}
