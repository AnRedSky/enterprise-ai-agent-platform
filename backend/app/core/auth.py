from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.security import decode_token

bearer = HTTPBearer(auto_error=False)


def current_claims(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    """Return decoded JWT claims for FastAPI injection or direct service/test calls."""
    # FastAPI resolves ``Depends(bearer)`` before invoking this function. Runtime
    # helpers also call ``current_claims()`` directly, in which case the default
    # value is a Depends marker rather than credentials. Check the resolved type
    # instead of using ``isinstance(..., Depends)`` because ``Depends`` is a
    # factory function, not the marker's runtime class.
    if not isinstance(credentials, HTTPAuthorizationCredentials):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="需要登录")
    try:
        return decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效或已过期")


def _normalize_roles(claims: dict) -> set[str]:
    roles = claims.get("roles", [])
    if isinstance(roles, str):
        roles = [roles]
    return {role for role in roles if isinstance(role, str)}


def require_roles(*required: str):
    def dependency(claims: dict = Depends(current_claims)):
        roles = _normalize_roles(claims)
        if "admin" not in roles and not roles.intersection(required):
            raise HTTPException(status_code=403, detail="权限不足")
        return claims

    return dependency
