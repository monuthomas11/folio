from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import (
    create_access_token,
    create_api_key,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _coerce_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=404, detail="API key not found")


@router.post("/register", response_model=schemas.TokenOut, status_code=201)
def register(payload: schemas.RegisterIn, db: Session = Depends(get_db)):
    existing = db.scalar(select(models.User).where(models.User.email == payload.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = models.User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id))
    return schemas.TokenOut(access_token=token, user=user)


@router.post("/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(str(user.id))
    return schemas.TokenOut(access_token=token, user=user)


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@router.get("/api-keys", response_model=list[schemas.APIKeyOut])
def list_api_keys(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(models.APIKey)
        .where(models.APIKey.user_id == user.id)
        .order_by(models.APIKey.created_at.desc())
    ).all()


@router.post("/api-keys", response_model=schemas.APIKeyCreatedOut, status_code=201)
def create_user_api_key(
    payload: schemas.APIKeyCreateIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    key, prefix, key_hash = create_api_key()
    api_key = models.APIKey(
        user_id=user.id,
        name=payload.name,
        key_prefix=prefix,
        key_hash=key_hash,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return schemas.APIKeyCreatedOut.model_validate({
        "id": api_key.id,
        "name": api_key.name,
        "key_prefix": api_key.key_prefix,
        "last_used_at": api_key.last_used_at,
        "revoked_at": api_key.revoked_at,
        "created_at": api_key.created_at,
        "key": key,
    })


@router.delete("/api-keys/{key_id}", status_code=204)
def revoke_api_key(
    key_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    api_key = db.scalar(
        select(models.APIKey).where(
            models.APIKey.id == _coerce_uuid(key_id),
            models.APIKey.user_id == user.id,
        )
    )
    if api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    api_key.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=204)


@router.delete("/api-keys/{key_id}/permanent", status_code=204)
def delete_revoked_api_key(
    key_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    api_key = db.scalar(
        select(models.APIKey).where(
            models.APIKey.id == _coerce_uuid(key_id),
            models.APIKey.user_id == user.id,
        )
    )
    if api_key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    if api_key.revoked_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Revoke the API key before deleting it",
        )
    db.delete(api_key)
    db.commit()
    return Response(status_code=204)
