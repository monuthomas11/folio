from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import get_external_api_user
from .watchlist import create_watchlist_item_record

router = APIRouter(prefix="/api/v1", tags=["external integrations"])


@router.post("/watchlist", response_model=schemas.WatchlistOut, status_code=201)
def add_watchlist_item_external(
    payload: schemas.WatchlistIn,
    user: models.User = Depends(get_external_api_user),
    db: Session = Depends(get_db),
):
    return create_watchlist_item_record(db, user, payload)
