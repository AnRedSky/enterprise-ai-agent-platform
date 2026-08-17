from datetime import datetime, timedelta, timezone
from uuid import UUID
from jose import jwt
from passlib.context import CryptContext
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_minutes: int = 60

settings = Settings()
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd.verify(password, hashed)

def create_token(user_id: UUID, roles: list[str]) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": str(user_id), "roles": roles, "exp": exp}, settings.secret_key, algorithm=settings.algorithm)
