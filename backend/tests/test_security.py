from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.auth import current_claims, require_roles
from app.core.security import create_token, decode_token, hash_password, verify_password


def test_password_hash_roundtrip():
    hashed = hash_password("StrongPass123!")
    assert hashed != "StrongPass123!"
    assert verify_password("StrongPass123!", hashed)


def test_jwt_roundtrip():
    user_id = uuid4()
    token = create_token(user_id, ["user"])
    claims = decode_token(token)
    assert claims["sub"] == str(user_id)
    assert claims["roles"] == ["user"]


def _authorization_app():
    app = FastAPI()

    @app.get("/protected")
    async def protected(claims: dict = Depends(require_roles("operator"))):
        return {"sub": claims["sub"]}

    return app


def test_require_roles_accepts_single_string_role_claim():
    app = _authorization_app()
    token = create_token(uuid4(), ["operator"])
    response = TestClient(app).get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_require_roles_rejects_unrelated_role():
    app = _authorization_app()
    token = create_token(uuid4(), ["user"])
    response = TestClient(app).get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_current_claims_requires_bearer_credentials():
    with pytest.raises(Exception) as exc_info:
        current_claims()
    assert getattr(exc_info.value, "status_code", None) == 401
