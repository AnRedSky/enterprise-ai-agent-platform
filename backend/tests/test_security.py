from uuid import uuid4
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
