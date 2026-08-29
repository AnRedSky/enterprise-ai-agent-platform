"""Runtime Provider 健康探测服务。

职责：对租户已注册 Provider 的显式 healthcheck endpoint 执行受控 HTTP 探测，并持久化健康状态。
边界：只允许注册配置中的显式 HTTPS healthcheck_url；禁止携带凭据、禁止跟随重定向，并复用统一 SSRF/出口安全策略。
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.runtime_operations import RuntimeProviderRegistry
from app.services.integration.security import DEFAULT_WEBHOOK_ENDPOINT_POLICY
from app.services.runtime_operations.enterprise import RuntimeOperationsEnterpriseService


@dataclass(frozen=True, slots=True)
class ProviderHealthResult:
    """描述一次 Provider 健康探测结果。"""

    provider_id: UUID
    status: str
    http_status: int | None
    latency_ms: float | None
    error: str | None


class RuntimeProviderHealthService:
    """执行 tenant-scoped Provider 健康探测并记录运维审计。"""

    async def probe(self, db: AsyncSession, tenant_id: UUID, provider_id: UUID, actor: str) -> ProviderHealthResult:
        """探测 Provider healthcheck_url 并更新健康状态。

        Args:
            db: 当前请求的异步数据库会话。
            tenant_id: 租户标识，决定 Provider 查询边界。
            provider_id: Provider 注册标识。
            actor: 执行探测的操作者标识。

        Returns:
            ProviderHealthResult，包含健康状态、HTTP 状态码与耗时。

        Raises:
            ValueError: Provider 不存在或未配置 healthcheck_url，或 endpoint 不符合统一出口安全策略。
        """
        provider = await db.scalar(select(RuntimeProviderRegistry).where(RuntimeProviderRegistry.id == provider_id, RuntimeProviderRegistry.tenant_id == tenant_id))
        if provider is None:
            raise ValueError("provider not found")
        healthcheck_url = str(provider.config.get("healthcheck_url", "")).strip()
        if not healthcheck_url:
            raise ValueError("provider healthcheck_url is not configured")
        DEFAULT_WEBHOOK_ENDPOINT_POLICY.validate(healthcheck_url)
        timeout_seconds = min(max(float(provider.config.get("healthcheck_timeout_seconds", 5)), 0.5), 10.0)

        started = perf_counter()
        status = "unhealthy"
        http_status: int | None = None
        error: str | None = None
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False) as client:
                response = await client.get(healthcheck_url)
                http_status = response.status_code
                status = "healthy" if 200 <= response.status_code < 300 else "unhealthy"
                if status == "unhealthy":
                    error = f"healthcheck returned HTTP {response.status_code}"
        except (httpx.HTTPError, OSError) as exc:
            error = type(exc).__name__
        latency_ms = round((perf_counter() - started) * 1000, 3)
        provider.health_status = status
        await RuntimeOperationsEnterpriseService(db).audit(tenant_id, actor, "provider.health_probe", "provider", str(provider.id), status, {"provider_name": provider.name, "provider_type": provider.provider_type, "http_status": http_status, "latency_ms": latency_ms, "error": error})
        return ProviderHealthResult(provider.id, status, http_status, latency_ms, error)
