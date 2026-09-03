from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any
import uuid

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import get_db

security = HTTPBearer(auto_error=False)
external_api_key_header = APIKeyHeader(name="X-Folio-API-Key", auto_error=False)
EXTERNAL_KEY_PREFIX = "folio_wk_"


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        return False


def create_api_key() -> tuple[str, str, str]:
    key = f"{EXTERNAL_KEY_PREFIX}{secrets.token_urlsafe(32)}"
    return key, key[:16], hashlib.sha256(key.encode("utf-8")).hexdigest()


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def get_external_api_user(
    request: Request,
    api_key: str | None = Depends(external_api_key_header),
    db: Session = Depends(get_db),
) -> models.User:
    from .services.api_rate_limiter import get_external_api_rate_limiter

    client_host = request.client.host if request.client else "unknown"
    limiter = get_external_api_rate_limiter()
    limiter.check(f"ip:{client_host}")
    if not api_key or not api_key.startswith(EXTERNAL_KEY_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    key_hash = hash_api_key(api_key)
    stored = db.scalar(
        select(models.APIKey).where(
            models.APIKey.key_prefix == api_key[:16],
            models.APIKey.key_hash == key_hash,
            models.APIKey.revoked_at.is_(None),
        )
    )
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    limiter.check(f"key:{key_hash}")
    stored.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return stored.user


def create_access_token(user_id: str, expires_minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> models.User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id_uuid = uuid.UUID(user_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.get(models.User, user_id_uuid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user
