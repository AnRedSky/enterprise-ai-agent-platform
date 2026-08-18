import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.dependencies.db import get_db
from app.models.core import Role, User, UserRole


class FakeResult:
    def __init__(self, value=None, values=None):
        self.value = value
        self.values = values if values is not None else []

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.values


class FakeDB:
    def __init__(self, user=None, role=None):
        self.user = user
        self.role = role
        self.added = []

    async def execute(self, statement):
        text = str(statement)
        if "FROM users" in text or "users" in text:
            return FakeResult(self.user)
        if "FROM roles" in text or "roles" in text:
            return FakeResult(self.role)
        return FakeResult()

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        for value in self.added:
            if isinstance(value, User) and value.id is None:
                from uuid import uuid4
                value.id = uuid4()
            if isinstance(value, Role) and value.id is None:
                from uuid import uuid4
                value.id = uuid4()

    async def commit(self):
        pass

    async def refresh(self, value):
        pass


@pytest.fixture
def db_override():
    db = FakeDB()

    async def override():
        yield db

    app.dependency_overrides[get_db] = override
    yield db
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_register_returns_user_payload(db_override):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json={"username": "tester", "password": "password123"})
    assert response.status_code == 200
    assert response.json()["username"] == "tester"
    assert response.json()["roles"] == ["user"]


@pytest.mark.asyncio
async def test_register_rejects_duplicate_user(db_override):
    from uuid import uuid4
    db_override.user = User(id=uuid4(), username="tester", password_hash="hash")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json={"username": "tester", "password": "password123"})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(db_override):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login", json={"username": "missing", "password": "password123"})
    assert response.status_code == 401
