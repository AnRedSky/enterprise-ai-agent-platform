from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_token, hash_password, verify_password
from app.dependencies.db import get_db
from app.models.core import Role, User, UserRole

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
    user = User(username=p.username, password_hash=hash_password(p.password))
    db.add(user)
    await db.flush()
    role = (await db.execute(select(Role).where(Role.name == "user"))).scalar_one_or_none()
    if not role:
        role = Role(name="user")
        db.add(role)
        await db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    await db.commit()
    await db.refresh(user)
    return {"user_id": user.id, "username": user.username, "tenant_id": user.tenant_id, "roles": ["user"]}


@router.post("/login")
async def login(p: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.username == p.username))).scalar_one_or_none()
    if not user or user.status != "active" or not verify_password(p.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    roles = await get_roles(db, user.id)
    return {
        "access_token": create_token(user.id, roles, tenant_id=user.tenant_id),
        "token_type": "bearer",
        "roles": roles,
        "tenant_id": user.tenant_id,
    }
