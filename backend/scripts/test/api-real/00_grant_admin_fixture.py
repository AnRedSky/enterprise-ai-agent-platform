from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.core.security import create_token
from app.dependencies.db import SessionLocal
from app.models.core import Role, User, UserRole

ENV_FILE = Path(__file__).with_name(".real_api_context.json")


async def grant_admin(user_id: UUID) -> str:
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        role = (await db.execute(select(Role).where(Role.name == "admin"))).scalar_one()
        existing = await db.execute(
            select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
        )
        if existing.scalar_one_or_none() is None:
            db.add(UserRole(user_id=user.id, role_id=role.id))
            await db.commit()
        return create_token(user.id, ["admin"], tenant_id=user.tenant_id)


def main() -> None:
    context = json.loads(ENV_FILE.read_text(encoding="utf-8"))
    user_id = UUID(context["ORGANIZATION_MEMBER_USER_ID"])
    context["ADMIN_ACCESS_TOKEN"] = asyncio.run(grant_admin(user_id))
    ENV_FILE.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
