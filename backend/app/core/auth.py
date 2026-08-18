from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.security import decode_token

bearer = HTTPBearer(auto_error=False)


def current_claims(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    """Return decoded JWT claims for FastAPI injection or direct service/test calls."""
    # FastAPI resolves ``Depends(bearer)`` before invoking this function. Runtime
    # helpers also call ``current_claims()`` directly, in which case the default
    # value is the Depends marker rather than credentials.
    if isinstance(credentials, Depends) or not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="需要登录")
    try:
        return decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效或已过期")


def require_roles(*required: str):
    def dependency(claims: dict = Depends(current_claims)):
        roles = set(claims.get("roles", []))
        if "admin" not in roles and not roles.intersection(required):
            raise HTTPException(status_code=403, detail="权限不足")
        return claims

    return dependency
