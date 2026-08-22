from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from app.services.organization import OrganizationService


@pytest.mark.asyncio
async def test_require_active_membership_rejects_inactive_user():
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: SimpleNamespace(status="suspended"))
    service = OrganizationService(db)

    with pytest.raises(HTTPException) as exc:
        await service.require_active_membership(uuid4(), uuid4())

    assert exc.value.status_code == 403
    assert "不可访问" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_add_member_rejects_owner_role_without_transfer():
    service = OrganizationService(AsyncMock())
    service.require_management_access = AsyncMock(return_value=SimpleNamespace(role="owner"))

    with pytest.raises(HTTPException) as exc:
        await service.add_member(uuid4(), uuid4(), uuid4(), role="owner")

    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_update_member_rejects_direct_owner_assignment():
    service = OrganizationService(AsyncMock())
    service.require_management_access = AsyncMock(return_value=SimpleNamespace(role="owner"))
    membership = SimpleNamespace(id=uuid4(), organization_id=uuid4(), role="member", status="active")
    service.db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: membership)

    with pytest.raises(HTTPException) as exc:
        await service.update_member(uuid4(), membership.id, uuid4(), role="owner")

    assert exc.value.status_code == 422
    assert "owner transfer" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_remove_unique_owner_is_rejected():
    service = OrganizationService(AsyncMock())
    service.require_management_access = AsyncMock(return_value=SimpleNamespace(role="owner"))
    membership = SimpleNamespace(id=uuid4(), organization_id=uuid4(), role="owner", status="active")
    service.db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: membership)
    service._ensure_owner_remains = AsyncMock(side_effect=HTTPException(409, "不能删除或降级唯一 owner"))

    with pytest.raises(HTTPException) as exc:
        await service.remove_member(membership.organization_id, membership.id, uuid4())

    assert exc.value.status_code == 409
    service._ensure_owner_remains.assert_awaited_once_with(membership.organization_id, membership.id)


def test_organization_domain_constants_match_contract():
    assert OrganizationService.ROLES == {"owner", "admin", "member"}
    assert OrganizationService.STATUSES == {"invited", "active", "suspended", "removed"}
    assert OrganizationService.MANAGEMENT_ROLES == {"owner", "admin"}
