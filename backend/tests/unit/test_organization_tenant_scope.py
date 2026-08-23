from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.core import User
from app.models.organization import Organization
from app.services.organization import OrganizationService


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _NestedTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, results):
        self._results = iter(results)
        self.added = []
        self.committed = False

    async def execute(self, _query):
        return _Result(next(self._results))

    def begin_nested(self):
        return _NestedTransaction()

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        return None

    async def commit(self):
        self.committed = True

    async def refresh(self, _item):
        return None


@pytest.mark.asyncio
async def test_create_organization_reuses_owner_tenant_for_runtime_governance():
    tenant_id = uuid4()
    owner = User(
        id=uuid4(),
        username="tenant-owner",
        password_hash="hashed",
        tenant_id=tenant_id,
        status="active",
    )
    db = _FakeSession([owner, None, None])

    organization = await OrganizationService(db).create("Runtime Governance Org", owner.id)

    assert organization.tenant_id == owner.tenant_id
    assert organization.tenant_id == tenant_id
    assert organization.name == "Runtime Governance Org"
    assert db.committed is True
    created_orgs = [item for item in db.added if isinstance(item, Organization)]
    assert len(created_orgs) == 1
    assert created_orgs[0].tenant_id == owner.tenant_id


@pytest.mark.asyncio
async def test_create_organization_rejects_second_organization_for_same_tenant():
    tenant_id = uuid4()
    owner = User(
        id=uuid4(),
        username="tenant-owner",
        password_hash="hashed",
        tenant_id=tenant_id,
        status="active",
    )
    existing = Organization(
        id=uuid4(),
        tenant_id=tenant_id,
        name="Existing Organization",
        status="active",
    )
    db = _FakeSession([owner, None, existing])

    with pytest.raises(HTTPException) as exc_info:
        await OrganizationService(db).create("Another Organization", owner.id)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "当前 Tenant 已存在 Organization"
    assert db.added == []
    assert db.committed is False
