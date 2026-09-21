import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from yfinance_service import fetch_ltp, fetch_ltps

from .. import models, schemas
from ..database import get_db
from ..security import get_current_user
from ..services.watchlist import evaluate_watchlist_item, update_watchlist_items

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


def _coerce_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=404, detail="Watchlist item not found")


def _get_owned_item(db: Session, user: models.User, item_id: str) -> models.WatchlistItem:
    item = db.scalar(
        select(models.WatchlistItem)
        .options(selectinload(models.WatchlistItem.levels))
        .where(
            models.WatchlistItem.id == _coerce_uuid(item_id),
            models.WatchlistItem.user_id == user.id,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    return item


def _normalized_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized:
        raise HTTPException(status_code=422, detail="Symbol is required")
    return normalized


def _add_levels(item: models.WatchlistItem, levels: list[schemas.WatchlistLevelIn]) -> None:
    item.levels = [
        models.WatchlistLevel(
            kind=level.kind,
            label=level.label.strip() if level.label and level.label.strip() else None,
            lower_price=level.lower_price,
            upper_price=level.upper_price,
            sort_order=index,
        )
        for index, level in enumerate(levels)
    ]


def _evaluate_item(db: Session, item: models.WatchlistItem) -> None:
    evaluate_watchlist_item(db, item)


@router.get("", response_model=list[schemas.WatchlistOut])
def list_watchlist(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(models.WatchlistItem)
        .options(selectinload(models.WatchlistItem.levels))
        .where(models.WatchlistItem.user_id == user.id)
        .order_by(models.WatchlistItem.created_at.desc())
    ).all()


def create_watchlist_item_record(
    db: Session, user: models.User, payload: schemas.WatchlistIn
) -> models.WatchlistItem:
    symbol = _normalized_symbol(payload.symbol)
    if db.scalar(
        select(models.WatchlistItem).where(
            models.WatchlistItem.user_id == user.id,
            models.WatchlistItem.symbol == symbol,
        )
    ):
        raise HTTPException(status_code=409, detail="That symbol is already on your watchlist")
    item = models.WatchlistItem(user_id=user.id, symbol=symbol, notes=payload.notes)
    _add_levels(item, payload.levels)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That symbol is already on your watchlist")
    db.refresh(item)
    return item


@router.post("", response_model=schemas.WatchlistOut, status_code=201)
def create_watchlist_item(
    payload: schemas.WatchlistIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_watchlist_item_record(db, user, payload)


@router.put("/{item_id}", response_model=schemas.WatchlistOut)
def update_watchlist_item(
    item_id: str,
    payload: schemas.WatchlistIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_owned_item(db, user, item_id)
    symbol = _normalized_symbol(payload.symbol)
    duplicate = db.scalar(
        select(models.WatchlistItem).where(
            models.WatchlistItem.user_id == user.id,
            models.WatchlistItem.symbol == symbol,
            models.WatchlistItem.id != item.id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="That symbol is already on your watchlist")
    item.symbol = symbol
    item.notes = payload.notes
    item.levels = []
    db.flush()
    _add_levels(item, payload.levels)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
def delete_watchlist_item(
    item_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _get_owned_item(db, user, item_id)
    db.delete(item)
    db.commit()


def _owned_items_for_symbol(db: Session, user: models.User, symbol: str) -> list[models.WatchlistItem]:
    return db.scalars(
        select(models.WatchlistItem)
        .options(selectinload(models.WatchlistItem.levels))
        .where(
            models.WatchlistItem.user_id == user.id,
            models.WatchlistItem.symbol == symbol,
        )
    ).all()


def _update_items(items: list[models.WatchlistItem], prices: dict[str, float], db: Session) -> None:
    update_watchlist_items(db, items, prices)


@router.post("/fetch-price/{symbol}", response_model=schemas.PriceOut)
def fetch_watchlist_price(
    symbol: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    normalized = _normalized_symbol(symbol)
    items = _owned_items_for_symbol(db, user, normalized)
    if not items:
        raise HTTPException(status_code=404, detail="No watchlist item with this symbol")
    try:
        ltp = fetch_ltp(normalized)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch price: {exc}")
    _update_items(items, {normalized: ltp}, db)
    db.commit()
    return schemas.PriceOut(symbol=normalized, ltp=ltp, last_updated=items[0].last_updated)


@router.post("/fetch-all", response_model=list[schemas.WatchlistOut])
def fetch_all_watchlist_prices(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = db.scalars(
        select(models.WatchlistItem)
        .options(selectinload(models.WatchlistItem.levels))
        .where(models.WatchlistItem.user_id == user.id)
    ).all()
    if not items:
        return []
    prices, errors = fetch_ltps({item.symbol for item in items})
    if not prices and errors:
        raise HTTPException(status_code=502, detail=f"Could not fetch prices: {next(iter(errors.values()))}")
    _update_items(items, prices, db)
    db.commit()
    return db.scalars(
        select(models.WatchlistItem)
        .options(selectinload(models.WatchlistItem.levels))
        .where(models.WatchlistItem.user_id == user.id)
        .order_by(models.WatchlistItem.created_at.desc())
    ).all()
