from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.dependencies.db import get_db
from app.main import app
from app.models.core import DEFAULT_TENANT_ID, Role, Tenant, User, UserRole
from app.models.organization import Organization, OrganizationMembership


class FakeResult:
    def __init__(self, value=None, values=None): self.value = value; self.values = values or []
    def scalar_one_or_none(self): return self.value
    def scalars(self): return self
    def all(self): return self.values


class FakeDB:
    def __init__(self, user=None, role=None, tenant=None, organization=None):
        self.user = user
        self.role = role
        self.tenant = tenant or Tenant(id=DEFAULT_TENANT_ID, name="Default Tenant", status="active")
        self.organization = organization or Organization(
            id=uuid4(),
            tenant_id=DEFAULT_TENANT_ID,
            name="Default Organization",
            status="active",
        )
        self.added = []
        self.raise_integrity_error = False
        self.rolled_back = False

    async def execute(self, statement):
        text = str(statement)
        if "users" in text: return FakeResult(self.user)
        if "tenants" in text: return FakeResult(self.tenant)
        if "organizations" in text: return FakeResult(self.organization)
        if "roles" in text: return FakeResult(self.role)
        return FakeResult()

    def add(self, value): self.added.append(value)

    async def flush(self):
        if self.raise_integrity_error:
            raise IntegrityError("flush", {}, Exception("duplicate key"))
        for value in self.added:
            if isinstance(value, (User, Role)) and value.id is None: value.id = uuid4()

    async def commit(self): pass
    async def rollback(self): self.rolled_back = True
    async def refresh(self, value): pass


@pytest.fixture
def db_override():
    db = FakeDB()
    async def override(): yield db
    app.dependency_overrides[get_db] = override
    yield db
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_register_returns_user_payload(db_override):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json={"username":"tester","password":"password123"})
    assert response.status_code == 200
    assert response.json()["username"] == "tester"
    assert response.json()["roles"] == ["user"]
    assert any(isinstance(value, User) for value in db_override.added)
    assert any(isinstance(value, UserRole) for value in db_override.added)
    assert any(isinstance(value, OrganizationMembership) for value in db_override.added)


@pytest.mark.asyncio
async def test_register_rejects_integrity_conflict(db_override):
    db_override.raise_integrity_error = True
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json={"username":"tester","password":"password123"})
    assert response.status_code == 409
    assert db_override.rolled_back is True


@pytest.mark.asyncio
async def test_register_rejects_missing_default_organization(db_override):
    db_override.organization = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json={"username":"tester","password":"password123"})
    assert response.status_code == 409
    assert db_override.rolled_back is True


@pytest.mark.asyncio
async def test_register_rejects_duplicate_user(db_override):
    db_override.user = User(id=uuid4(), username="tester", password_hash="hash")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json={"username":"tester","password":"password123"})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(db_override):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login", json={"username":"missing","password":"password123"})
    assert response.status_code == 401
