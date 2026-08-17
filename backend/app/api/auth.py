from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.db import get_db
from app.models.core import User
from app.core.security import hash_password, verify_password, create_token

router = APIRouter()
class RegisterRequest(BaseModel): username: str = Field(min_length=3); password: str = Field(min_length=8)
class LoginRequest(RegisterRequest): pass

@router.post("/register")
async def register(p: RegisterRequest, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(select(User).where(User.username == p.username))).scalar_one_or_none()
    if exists: raise HTTPException(409, "用户名已存在")
    user = User(username=p.username, password_hash=hash_password(p.password)); db.add(user); await db.commit(); await db.refresh(user)
    return {"user_id": user.id, "username": user.username, "roles": ["user"]}

@router.post("/login")
async def login(p: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.username == p.username))).scalar_one_or_none()
    if not user or not verify_password(p.password, user.password_hash): raise HTTPException(401, "用户名或密码错误")
    return {"access_token": create_token(user.id, ["user"]), "token_type": "bearer"}
