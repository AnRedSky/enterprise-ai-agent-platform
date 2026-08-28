from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_token, hash_password, verify_password
from app.dependencies.db import get_db
from app.models.core import DEFAULT_TENANT_ID, Role, Tenant, User, UserRole
from app.models.organization import Organization, OrganizationMembership

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(RegisterRequest):
    pass


async def get_roles(db, user_id):
    result = await db.execute(select(Role.name).join(UserRole, Role.id == UserRole.role_id).where(UserRole.user_id == user_id))
    roles = list(result.scalars().all())
    return roles or ["user"]


@router.post("/register")
async def register(p: RegisterRequest, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(select(User).where(User.username == p.username))).scalar_one_or_none()
    if exists:
        raise HTTPException(409, "用户名已存在")

    try:
        # 注册用户必须同时进入当前默认 Tenant 对应的 Organization，避免认证成功后因缺少 membership 无法访问受治理能力。
        tenant = (await db.execute(select(Tenant).where(Tenant.id == DEFAULT_TENANT_ID))).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(id=DEFAULT_TENANT_ID, name="Default Tenant", status="active")
            db.add(tenant)
            await db.flush()

        organization = (await db.execute(select(Organization).where(Organization.tenant_id == DEFAULT_TENANT_ID))).scalar_one_or_none()
        if organization is None:
            raise HTTPException(409, "默认 Tenant 尚未初始化 Organization")
        if organization.status != "active":
            raise HTTPException(409, "默认 Organization 当前不可用")

        role = (await db.execute(select(Role).where(Role.name == "user"))).scalar_one_or_none()
        if role is None:
            role = Role(name="user")
            db.add(role)
            await db.flush()

        user = User(username=p.username, password_hash=hash_password(p.password), tenant_id=DEFAULT_TENANT_ID)
        db.add(user)
        await db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.add(
            OrganizationMembership(
                organization_id=organization.id,
                user_id=user.id,
                status="active",
                role="member",
            )
        )
        await db.commit()
        await db.refresh(user)
    except HTTPException:
        await db.rollback()
        raise
    except IntegrityError as exc:
        await db.rollback()
        # 并发注册或历史数据不一致必须转换为稳定的业务冲突，而不是泄漏为 HTTP 500。
        raise HTTPException(409, "用户注册发生数据冲突，请重试") from exc

    return {"user_id": user.id, "username": user.username, "tenant_id": user.tenant_id, "roles": ["user"]}


@router.post("/login")
async def login(p: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.username == p.username))).scalar_one_or_none()
    if not user or user.status != "active" or not verify_password(p.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    roles = await get_roles(db, user.id)
    return {
        "user_id": user.id,
        "access_token": create_token(user.id, roles, tenant_id=user.tenant_id),
        "token_type": "bearer",
        "roles": roles,
        "tenant_id": user.tenant_id,
    }
