"""Model Provider/Profile 领域服务。

模块职责：管理组织内 Model Provider 与 Model Profile，并执行权限、校验、审计和路由查询。
边界：不实现外部模型调用；具体 Provider 适配位于 infrastructure/providers，不在领域 Service 中复制。
关键外部依赖：SQLAlchemy AsyncSession、ModelProvider/ModelProfile ORM 与 OrganizationService。
"""

from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import AuditLog
from app.models.model_provider import ModelProfile, ModelProvider
from app.models.organization import Organization, OrganizationMembership
from app.services.organization import OrganizationService

from .contract import ProviderCandidate, RoutingRequest, RoutingStrategy
from .routing import select_candidates


class ModelProviderService:
    MODEL_TYPES = {"chat", "embedding"}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.organizations = OrganizationService(db)

    async def require_management(self, organization_id: UUID, user_id: UUID) -> None:
        await self.organizations.require_management_access(organization_id, user_id)

    async def list_providers(self, organization_id: UUID, user_id: UUID, offset: int, limit: int):
        await self.organizations.require_active_membership(organization_id, user_id)
        query = select(ModelProvider).where(ModelProvider.organization_id == organization_id).order_by(ModelProvider.name.asc())
        total = int((await self.db.execute(
            select(func.count(ModelProvider.id)).where(ModelProvider.organization_id == organization_id)
        )).scalar_one())
        items = list((await self.db.execute(query.offset(offset).limit(limit))).scalars().all())
        return items, total

    async def get_provider(self, provider_id: UUID, user_id: UUID) -> ModelProvider:
        provider = (await self.db.execute(select(ModelProvider).where(ModelProvider.id == provider_id))).scalar_one_or_none()
        if provider is None:
            raise HTTPException(404, "Model Provider 不存在")
        await self.organizations.require_active_membership(provider.organization_id, user_id)
        return provider

    async def resolve_routing(self, payload, user_id: UUID):
        await self.organizations.require_active_membership(payload.organization_id, user_id)
        query = (
            select(ModelProfile, ModelProvider)
            .join(ModelProvider, ModelProvider.id == ModelProfile.provider_id)
            .join(Organization, Organization.id == ModelProvider.organization_id)
            .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
            .where(
                ModelProvider.organization_id == payload.organization_id,
                ModelProfile.model_type == payload.model_type,
                ModelProfile.enabled.is_(True),
                ModelProvider.enabled.is_(True),
                Organization.status == "active",
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.status == "active",
            )
        )
        rows = (await self.db.execute(query)).all()
        candidates = [
            ProviderCandidate(
                provider_id=provider.id,
                profile_id=profile.id,
                model_type=profile.model_type,
                model_name=profile.model_name,
                enabled=profile.enabled and provider.enabled,
                is_default=profile.is_default,
                capabilities=frozenset(key for key, value in (profile.capabilities or {}).items() if value is True),
                provider_name=provider.provider_name,
            )
            for profile, provider in rows
        ]
        request = RoutingRequest(
            organization_id=payload.organization_id,
            model_type=payload.model_type,
            profile_id=payload.profile_id,
            required_capabilities=frozenset(payload.required_capabilities),
            allowed_provider_ids=frozenset(payload.allowed_provider_ids),
        )
        return select_candidates(request, candidates, RoutingStrategy(payload.routing_strategy))

    async def create_provider(self, payload, user_id: UUID, request_id: str | None, trace_id: str | None):
        await self.require_management(payload.organization_id, user_id)
        provider = ModelProvider(
            id=uuid4(), organization_id=payload.organization_id, name=payload.name.strip(),
            provider_type=payload.provider_type.strip(), provider_name=payload.provider_name.strip(),
            endpoint=payload.endpoint, credential_ref=payload.credential_ref,
            enabled=payload.enabled, metadata_json=payload.metadata,
        )
        if not provider.name or not provider.provider_type or not provider.provider_name:
            raise HTTPException(422, "Provider 名称、类型和供应商名称不能为空")
        try:
            async with self.db.begin_nested():
                self.db.add(provider)
                await self.db.flush()
                self._audit(user_id, provider.organization_id, provider.id, "model_provider.created", request_id, trace_id)
        except IntegrityError as exc:
            raise HTTPException(409, "Provider 名称已存在") from exc
        await self.db.commit()
        await self.db.refresh(provider)
        return provider

    async def update_provider(self, provider_id: UUID, payload, user_id: UUID, request_id: str | None, trace_id: str | None):
        provider = await self.get_provider(provider_id, user_id)
        await self.require_management(provider.organization_id, user_id)
        if payload.name is not None:
            provider.name = payload.name.strip()
            if not provider.name:
                raise HTTPException(422, "Provider 名称不能为空")
        if payload.endpoint is not None:
            provider.endpoint = payload.endpoint
        if payload.credential_ref is not None:
            provider.credential_ref = payload.credential_ref
        if payload.enabled is not None:
            provider.enabled = payload.enabled
        if payload.metadata is not None:
            provider.metadata_json = payload.metadata
        self._audit(user_id, provider.organization_id, provider.id, "model_provider.updated", request_id, trace_id)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(409, "Provider 名称已存在") from exc
        await self.db.refresh(provider)
        return provider

    async def delete_provider(self, provider_id: UUID, user_id: UUID, request_id: str | None, trace_id: str | None):
        provider = await self.get_provider(provider_id, user_id)
        await self.require_management(provider.organization_id, user_id)
        profiles = int((await self.db.execute(
            select(func.count(ModelProfile.id)).where(ModelProfile.provider_id == provider.id)
        )).scalar_one())
        if profiles:
            raise HTTPException(409, "Provider 仍有 Model Profile，不能删除")
        self._audit(user_id, provider.organization_id, provider.id, "model_provider.deleted", request_id, trace_id)
        await self.db.delete(provider)
        await self.db.commit()

    async def list_profiles(self, provider_id: UUID, user_id: UUID):
        provider = await self.get_provider(provider_id, user_id)
        items = list((await self.db.execute(
            select(ModelProfile).where(ModelProfile.provider_id == provider.id).order_by(ModelProfile.model_type, ModelProfile.name)
        )).scalars().all())
        return provider, items

    async def create_profile(self, provider_id: UUID, payload, user_id: UUID, request_id: str | None, trace_id: str | None):
        provider = await self.get_provider(provider_id, user_id)
        await self.require_management(provider.organization_id, user_id)
        if payload.model_type not in self.MODEL_TYPES:
            raise HTTPException(422, "不支持的 Model Profile 类型")
        if payload.model_type == "embedding" and payload.dimension is None:
            raise HTTPException(422, "embedding Model Profile 必须声明 dimension")
        if payload.model_type == "chat" and payload.dimension is not None:
            raise HTTPException(422, "chat Model Profile 不应声明 embedding dimension")
        if payload.is_default:
            await self._clear_default(provider.id, payload.model_type)
        profile = ModelProfile(
            id=uuid4(), provider_id=provider.id, name=payload.name.strip(), model_type=payload.model_type,
            model_name=payload.model_name.strip(), dimension=payload.dimension,
            capabilities=payload.capabilities, parameters=payload.parameters,
            enabled=payload.enabled, is_default=payload.is_default,
        )
        if not profile.name or not profile.model_name:
            raise HTTPException(422, "Model Profile 名称不能为空")
        try:
            async with self.db.begin_nested():
                self.db.add(profile)
                await self.db.flush()
                self._audit(user_id, provider.organization_id, profile.id, "model_profile.created", request_id, trace_id)
        except IntegrityError as exc:
            raise HTTPException(409, "Model Profile 名称已存在") from exc
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def update_profile(self, profile_id: UUID, payload, user_id: UUID, request_id: str | None, trace_id: str | None):
        profile = (await self.db.execute(select(ModelProfile).where(ModelProfile.id == profile_id))).scalar_one_or_none()
        if profile is None:
            raise HTTPException(404, "Model Profile 不存在")
        provider = await self.get_provider(profile.provider_id, user_id)
        await self.require_management(provider.organization_id, user_id)
        if payload.name is not None:
            profile.name = payload.name.strip()
        if payload.model_name is not None:
            profile.model_name = payload.model_name.strip()
        if payload.dimension is not None:
            if profile.model_type != "embedding":
                raise HTTPException(422, "只有 embedding Model Profile 可以设置 dimension")
            profile.dimension = payload.dimension
        if payload.capabilities is not None:
            profile.capabilities = payload.capabilities
        if payload.parameters is not None:
            profile.parameters = payload.parameters
        if payload.enabled is not None:
            profile.enabled = payload.enabled
        if payload.is_default is True:
            await self._clear_default(profile.provider_id, profile.model_type, exclude_id=profile.id)
            profile.is_default = True
        elif payload.is_default is False:
            profile.is_default = False
        self._audit(user_id, provider.organization_id, profile.id, "model_profile.updated", request_id, trace_id)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(409, "Model Profile 更新冲突") from exc
        await self.db.refresh(profile)
        return profile

    async def delete_profile(self, profile_id: UUID, user_id: UUID, request_id: str | None, trace_id: str | None):
        profile = (await self.db.execute(select(ModelProfile).where(ModelProfile.id == profile_id))).scalar_one_or_none()
        if profile is None:
            raise HTTPException(404, "Model Profile 不存在")
        provider = await self.get_provider(profile.provider_id, user_id)
        await self.require_management(provider.organization_id, user_id)
        self._audit(user_id, provider.organization_id, profile.id, "model_profile.deleted", request_id, trace_id)
        await self.db.delete(profile)
        await self.db.commit()

    async def _clear_default(self, provider_id: UUID, model_type: str, exclude_id: UUID | None = None) -> None:
        query = select(ModelProfile).where(
            ModelProfile.provider_id == provider_id,
            ModelProfile.model_type == model_type,
            ModelProfile.is_default.is_(True),
        )
        if exclude_id is not None:
            query = query.where(ModelProfile.id != exclude_id)
        for item in (await self.db.execute(query)).scalars().all():
            item.is_default = False

    def _audit(self, actor_id: UUID, organization_id: UUID, resource_id: UUID, action: str, request_id: str | None, trace_id: str | None) -> None:
        self.db.add(AuditLog(
            actor_id=actor_id,
            tenant_id=None,
            action=action,
            resource_type="model_provider" if action.startswith("model_provider") else "model_profile",
            resource_id=str(resource_id),
            request_id=request_id,
            trace_id=trace_id,
            status="success",
            metadata_json={"organization_id": str(organization_id)},
        ))
