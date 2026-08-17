from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException
from jose import jwt, JWTError
from app.core.security import settings
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
def current_claims(token: str = Depends(oauth2)):
    try: return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError: raise HTTPException(401, "无效或过期的 Token")
