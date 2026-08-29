"""Tenant-scoped Webhook Destination registry lifecycle service."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_integration import WebhookDestination
from app.services.runtime_operations.enterprise import RuntimeOperationsEnterpriseService


class DestinationRegistryService:
    """Own destination configuration lifecycle while preserving runtime boundaries."""

    _FORBIDDEN_HEADERS = frozenset({"authorization", "proxy-authorization", "cookie", "set-cookie"})

    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit_service = RuntimeOperationsEnterpriseService(db)

    @staticmethod
    def _validate_url(endpoint_url: str) -> None:
        parsed = urlparse(endpoint_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("destination endpoint_url must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password:
            raise ValueError("destination endpoint_url must not contain embedded credentials")

    @classmethod
    def _validate_headers(cls, headers: dict[str, str] | None) -> dict[str, str]:
        if headers is None:
            return {}
        if not isinstance(headers, dict) or len(headers) > 50:
            raise ValueError("destination headers must be an object with at most 50 entries")
        for key, value in headers.items():
            if not isinstance(key, str) or not key.strip() or not isinstance(value, str):
                raise ValueError("destination headers must contain string keys and values")
            if key.lower() in cls._FORBIDDEN_HEADERS:
                raise ValueError("destination headers must not contain credential-bearing headers")
        return dict(headers)

    async def list(self, tenant_id: UUID) -> list[WebhookDestination]:
        return list((await self.db.execute(
            select(WebhookDestination)
            .where(WebhookDestination.tenant_id == tenant_id)
            .order_by(WebhookDestination.name, WebhookDestination.id)
        )).scalars().all())

    async def create(
        self,
        tenant_id: UUID,
        *,
        name: str,
        endpoint_url: str,
        actor: str,
        secret_ref: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> WebhookDestination:
        normalized_name = name.strip()
        if not 1 <= len(normalized_name) <= 120:
            raise ValueError("destination name must contain 1 to 120 characters")
        self._validate_url(endpoint_url)
        if secret_ref is not None and not 1 <= len(secret_ref.strip()) <= 500:
            raise ValueError("secret_ref must contain 1 to 500 characters")
        normalized_headers = self._validate_headers(headers)
        item = WebhookDestination(
            tenant_id=tenant_id,
            name=normalized_name,
            endpoint_url=endpoint_url,
            secret_ref=secret_ref.strip() if secret_ref else None,
            headers=normalized_headers,
            enabled=True,
        )
        self.db.add(item)
        await self.db.flush()
        parsed = urlparse(endpoint_url)
        await self.audit_service.audit(
            tenant_id,
            actor,
            "destination.create",
            "destination",
            str(item.id),
            "success",
            {"name": normalized_name, "scheme": parsed.scheme, "host": parsed.hostname},
        )
        return item

    async def set_enabled(self, tenant_id: UUID, destination_id: UUID, *, enabled: bool, actor: str) -> WebhookDestination:
        item = await self.db.scalar(select(WebhookDestination).where(
            WebhookDestination.tenant_id == tenant_id,
            WebhookDestination.id == destination_id,
        ))
        if item is None:
            raise ValueError("destination not found")
        item.enabled = enabled
        await self.db.flush()
        await self.audit_service.audit(
            tenant_id,
            actor,
            "destination.enable" if enabled else "destination.disable",
            "destination",
            str(destination_id),
            "success",
            {"enabled": enabled},
        )
        return item

    async def update(
        self,
        tenant_id: UUID,
        destination_id: UUID,
        *,
        actor: str,
        name: str | None = None,
        endpoint_url: str | None = None,
        secret_ref: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> WebhookDestination:
        """Update only fields supplied by the caller; never accepts credential values."""
        item = await self.db.scalar(select(WebhookDestination).where(
            WebhookDestination.tenant_id == tenant_id,
            WebhookDestination.id == destination_id,
        ))
        if item is None:
            raise ValueError("destination not found")
        if name is not None:
            normalized_name = name.strip()
            if not 1 <= len(normalized_name) <= 120:
                raise ValueError("destination name must contain 1 to 120 characters")
            item.name = normalized_name
        if endpoint_url is not None:
            self._validate_url(endpoint_url)
            item.endpoint_url = endpoint_url
        if secret_ref is not None:
            if not 1 <= len(secret_ref.strip()) <= 500:
                raise ValueError("secret_ref must contain 1 to 500 characters")
            item.secret_ref = secret_ref.strip()
        if headers is not None:
            item.headers = self._validate_headers(headers)
        await self.db.flush()
        await self.audit_service.audit(
            tenant_id,
            actor,
            "destination.update",
            "destination",
            str(destination_id),
            "success",
            {"fields": [key for key, value in {
                "name": name, "endpoint_url": endpoint_url,
                "secret_ref": secret_ref, "headers": headers,
            }.items() if value is not None]},
        )
        return item


__all__ = ["DestinationRegistryService"]
