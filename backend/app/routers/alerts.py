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
    holding_query = select(models.Alert).where(models.Alert.user_id == user.id)
    watchlist_query = select(models.WatchlistAlert).where(
        models.WatchlistAlert.user_id == user.id
    )
    if not include_dismissed:
        holding_query = holding_query.where(models.Alert.dismissed.is_(False))
        watchlist_query = watchlist_query.where(models.WatchlistAlert.dismissed.is_(False))
    alerts = list(db.scalars(holding_query).all()) + list(db.scalars(watchlist_query).all())
    return sorted(alerts, key=lambda alert: alert.created_at, reverse=True)


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
        alert = db.scalar(
            select(models.WatchlistAlert).where(
                models.WatchlistAlert.id == _coerce_uuid(alert_id),
                models.WatchlistAlert.user_id == user.id,
            )
        )
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    alert.dismissed = True
    db.commit()
    db.refresh(alert)
    return alert
