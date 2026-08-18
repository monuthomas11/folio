from fastapi import APIRouter, Depends, HTTPException, status
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _coerce_uuid(value: str, detail: str = "Alert not found") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


@router.get("", response_model=list[schemas.AlertOut])
def list_alerts(
    include_dismissed: bool = False,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(models.Alert).where(models.Alert.user_id == user.id)
    if not include_dismissed:
        query = query.where(models.Alert.dismissed.is_(False))
    return db.scalars(
        query.order_by(models.Alert.created_at.desc())
    ).all()


@router.put("/{alert_id}/dismiss", response_model=schemas.AlertOut)
def dismiss_alert(
    alert_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    alert = db.scalar(
        select(models.Alert).where(
            models.Alert.id == _coerce_uuid(alert_id),
            models.Alert.user_id == user.id,
        )
    )
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )
    alert.dismissed = True
    db.commit()
    db.refresh(alert)
    return alert