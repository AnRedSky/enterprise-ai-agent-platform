from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Tenant, User
from app.models.organization import Organization, OrganizationMembership


class OrganizationService:
    ROLES = {"owner", "admin", "member"}
    STATUSES = {"invited", "active", "suspended", "removed"}
    MANAGEMENT_ROLES = {"owner", "admin"}

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, organization_id: UUID) -> Organization:
        organization = (await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )).scalar_one_or_none()
        if organization is None:
            raise HTTPException(404, "Organization 不存在")
        return organization

    async def get_for_tenant(self, tenant_id: UUID) -> Organization:
        organization = (await self.db.execute(
            select(Organization).where(Organization.tenant_id == tenant_id)
        )).scalar_one_or_none()
        if organization is None:
            raise HTTPException(404, "Organization 不存在")
        return organization

    async def membership(self, organization_id: UUID, user_id: UUID) -> OrganizationMembership | None:
        return (await self.db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == user_id,
            )
        )).scalar_one_or_none()

    async def require_active_membership(
        self, organization_id: UUID, user_id: UUID
    ) -> OrganizationMembership:
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None or user.status != "active":
            raise HTTPException(403, "用户当前不可访问 Organization")
        membership = await self.membership(organization_id, user_id)
        if membership is None or membership.status != "active":
            raise HTTPException(403, "当前用户没有有效的 Organization membership")
        return membership

    async def require_management_access(
        self, organization_id: UUID, user_id: UUID
    ) -> OrganizationMembership:
        membership = await self.require_active_membership(organization_id, user_id)
        if membership.role not in self.MANAGEMENT_ROLES:
            raise HTTPException(403, "Organization 管理权限不足")
        return membership

    async def create(self, name: str, owner_user_id: UUID) -> Organization:
        normalized_name = name.strip()
        if not normalized_name:
            raise HTTPException(422, "Organization 名称不能为空")
        owner = (await self.db.execute(select(User).where(User.id == owner_user_id))).scalar_one_or_none()
        if owner is None or owner.status != "active":
            raise HTTPException(403, "创建 Organization 的用户不可用")
        existing = (await self.db.execute(
            select(Organization).where(Organization.name == normalized_name)
        )).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(409, "Organization 名称已存在")

        tenant = Tenant(id=uuid4(), name=normalized_name, status="active")
        organization = Organization(tenant_id=tenant.id, name=normalized_name, status="active")
        membership = OrganizationMembership(
            organization_id=organization.id,
            user_id=owner_user_id,
            status="active",
            role="owner",
        )
        try:
            async with self.db.begin_nested():
                self.db.add(tenant)
                self.db.add(organization)
                self.db.add(membership)
                await self.db.flush()
        except IntegrityError as exc:
            raise HTTPException(409, "Organization 创建冲突") from exc
        await self.db.commit()
        await self.db.refresh(organization)
        return organization

    async def add_member(
        self, organization_id: UUID, actor_id: UUID, user_id: UUID, role: str = "member"
    ) -> OrganizationMembership:
        if role not in self.ROLES:
            raise HTTPException(422, "不支持的 Organization role")
        await self.require_management_access(organization_id, actor_id)
        if role == "owner":
            raise HTTPException(422, "新增成员不能直接授予 owner，请使用 owner transfer")
        organization = await self.get(organization_id)
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            raise HTTPException(404, "用户不存在")
        if user.status != "active":
            raise HTTPException(409, "用户当前不可加入 Organization")
        existing = await self.membership(organization_id, user_id)
        if existing is not None:
            raise HTTPException(409, "用户已经属于该 Organization")
        membership = OrganizationMembership(
            organization_id=organization.id, user_id=user.id, status="active", role=role
        )
        try:
            async with self.db.begin_nested():
                self.db.add(membership)
                await self.db.flush()
        except IntegrityError as exc:
            raise HTTPException(409, "用户已经属于该 Organization") from exc
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def update_member(
        self,
        organization_id: UUID,
        membership_id: UUID,
        actor_id: UUID,
        *,
        role: str | None = None,
        status: str | None = None,
    ) -> OrganizationMembership:
        actor = await self.require_management_access(organization_id, actor_id)
        membership = (await self.db.execute(select(OrganizationMembership).where(
            OrganizationMembership.id == membership_id,
            OrganizationMembership.organization_id == organization_id,
        ))).scalar_one_or_none()
        if membership is None:
            raise HTTPException(404, "Membership 不存在")
        if role is not None and role not in self.ROLES:
            raise HTTPException(422, "不支持的 Organization role")
        if status is not None and status not in self.STATUSES:
            raise HTTPException(422, "不支持的 Membership 状态")
        if membership.role == "owner" and actor.role != "owner":
            raise HTTPException(403, "只有 owner 可以修改 owner membership")
        if membership.role == "owner" and role in {"admin", "member"}:
            await self._ensure_owner_remains(organization_id, membership.id)
        if role == "owner" and actor.role != "owner":
            raise HTTPException(403, "只有 owner 可以授予 owner role")
        if role is not None:
            membership.role = role
        if status is not None:
            membership.status = status
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def remove_member(
        self, organization_id: UUID, membership_id: UUID, actor_id: UUID
    ) -> None:
        actor = await self.require_management_access(organization_id, actor_id)
        membership = (await self.db.execute(select(OrganizationMembership).where(
            OrganizationMembership.id == membership_id,
            OrganizationMembership.organization_id == organization_id,
        ))).scalar_one_or_none()
        if membership is None:
            raise HTTPException(404, "Membership 不存在")
        if membership.role == "owner":
            if actor.role != "owner":
                raise HTTPException(403, "只有 owner 可以管理 owner membership")
            await self._ensure_owner_remains(organization_id, membership.id)
        # Keep the record for audit/history; removal is a lifecycle transition.
        membership.status = "removed"
        await self.db.commit()

    async def transfer_owner(
        self, organization_id: UUID, actor_id: UUID, target_membership_id: UUID
    ) -> OrganizationMembership:
        actor = await self.require_active_membership(organization_id, actor_id)
        if actor.role != "owner":
            raise HTTPException(403, "只有当前 owner 可以转移 owner")
        result = await self.db.execute(
            select(OrganizationMembership)
            .where(OrganizationMembership.organization_id == organization_id)
            .with_for_update()
        )
        memberships = list(result.scalars().all())
        target = next((item for item in memberships if item.id == target_membership_id), None)
        if target is None:
            raise HTTPException(404, "Membership 不存在")
        if target.status != "active":
            raise HTTPException(409, "只有 active membership 可以成为 owner")
        current_owners = [item for item in memberships if item.role == "owner" and item.status == "active"]
        if len(current_owners) != 1 or current_owners[0].id != actor.id:
            raise HTTPException(409, "Organization owner 状态异常")
        current_owners[0].role = "admin"
        target.role = "owner"
        await self.db.commit()
        await self.db.refresh(target)
        return target

    async def _ensure_owner_remains(self, organization_id: UUID, membership_id: UUID) -> None:
        result = await self.db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.status == "active",
                OrganizationMembership.role == "owner",
                OrganizationMembership.id != membership_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(409, "不能删除或降级唯一 owner，请先转移 owner")
