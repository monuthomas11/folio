from datetime import date, datetime, timezone
from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from yfinance_service import fetch_price_data

from .. import models, schemas
from ..database import get_db
from ..security import get_current_user

router = APIRouter(prefix="/tradebook", tags=["tradebook"])


def _coerce_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=404, detail="Trade not found")


def _get_owned_trade(db: Session, user: models.User, trade_id: str) -> models.Trade:
    trade = db.scalar(
        select(models.Trade)
        .options(selectinload(models.Trade.exits))
        .where(
            models.Trade.id == _coerce_uuid(trade_id),
            models.Trade.user_id == user.id,
        )
    )
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


def _dec(value: float | Decimal | None) -> Decimal:
    return Decimal(str(value or 0))


def _trade_values(trade: models.Trade) -> tuple[Decimal, Decimal, Decimal | None, Decimal | None]:
    entry_quantity = _dec(trade.entry_quantity)
    entry_price = _dec(trade.entry_price)
    exited_quantity = sum((_dec(item.quantity) for item in trade.exits), Decimal("0"))
    remaining = max(Decimal("0"), entry_quantity - exited_quantity)
    realized = Decimal("0")
    for item in trade.exits:
        quantity = _dec(item.quantity)
        exit_price = _dec(item.exit_price)
        if trade.side == "long":
            realized += (exit_price - entry_price) * quantity
        else:
            realized += (entry_price - exit_price) * quantity

    unrealized: Decimal | None = None
    if remaining > 0 and trade.current_ltp is not None:
        ltp = _dec(trade.current_ltp)
        unrealized = (ltp - entry_price) * remaining if trade.side == "long" else (entry_price - ltp) * remaining
    total = realized + unrealized if unrealized is not None else None
    return remaining, realized, unrealized, total


def _trade_out(trade: models.Trade) -> dict:
    remaining, realized, unrealized, total = _trade_values(trade)
    entry_price = _dec(trade.entry_price)
    exits = []
    for item in trade.exits:
        exit_price = _dec(item.exit_price)
        quantity = _dec(item.quantity)
        pnl = (exit_price - entry_price) * quantity if trade.side == "long" else (entry_price - exit_price) * quantity
        exits.append(
            {
                "id": item.id,
                "quantity": float(quantity),
                "exit_price": float(exit_price),
                "exit_date": item.exit_date,
                "realized_pnl": round(float(pnl), 2),
            }
        )
    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "side": trade.side,
        "entry_date": trade.entry_date,
        "entry_quantity": float(_dec(trade.entry_quantity)),
        "entry_price": float(entry_price),
        "broker": trade.broker,
        "notes": trade.notes,
        "current_ltp": float(trade.current_ltp) if trade.current_ltp is not None else None,
        "last_updated": trade.last_updated,
        "remaining_quantity": float(remaining),
        "status": "closed" if remaining == 0 else "open",
        "realized_pnl": round(float(realized), 2),
        "unrealized_pnl": round(float(unrealized), 2) if unrealized is not None else None,
        "total_pnl": round(float(total), 2) if total is not None else None,
        "exits": exits,
    }


def _list_owned_trades(db: Session, user: models.User) -> list[models.Trade]:
    return list(
        db.scalars(
            select(models.Trade)
            .options(selectinload(models.Trade.exits))
            .where(models.Trade.user_id == user.id)
            .order_by(models.Trade.entry_date.desc(), models.Trade.created_at.desc())
        ).all()
    )


def _tradebook_response(trades: list[models.Trade]) -> dict:
    rows = [_trade_out(trade) for trade in trades]
    realized = sum((Decimal(str(row["realized_pnl"])) for row in rows), Decimal("0"))
    open_rows = [row for row in rows if row["status"] == "open"]
    priced_rows = [row for row in open_rows if row["unrealized_pnl"] is not None]
    unpriced_count = len(open_rows) - len(priced_rows)
    unrealized = sum((Decimal(str(row["unrealized_pnl"])) for row in priced_rows), Decimal("0")) if priced_rows else None
    total = realized + unrealized if unpriced_count == 0 and unrealized is not None else (realized if not open_rows else None)
    return {
        "summary": {
            "trade_count": len(rows),
            "open_count": len(open_rows),
            "closed_count": len(rows) - len(open_rows),
            "realized_pnl": round(float(realized), 2),
            "unrealized_pnl": round(float(unrealized), 2) if unrealized is not None else None,
            "total_pnl": round(float(total), 2) if total is not None else None,
            "unpriced_open_count": unpriced_count,
        },
        "trades": rows,
    }


@router.get("", response_model=schemas.TradebookOut)
def get_tradebook(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _tradebook_response(_list_owned_trades(db, user))


@router.post("", response_model=schemas.TradeOut, status_code=status.HTTP_201_CREATED)
def create_trade(
    payload: schemas.TradeIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trade = models.Trade(
        user_id=user.id,
        symbol=payload.symbol.strip().upper(),
        side=payload.side,
        entry_date=payload.entry_date,
        entry_quantity=payload.entry_quantity,
        entry_price=payload.entry_price,
        broker=payload.broker,
        notes=payload.notes,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    trade.exits = []
    return _trade_out(trade)


@router.put("/{trade_id}", response_model=schemas.TradeOut)
def update_trade(
    trade_id: str,
    payload: schemas.TradeIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trade = _get_owned_trade(db, user, trade_id)
    if trade.exits:
        raise HTTPException(status_code=409, detail="Trades cannot be edited after an exit is recorded")
    trade.symbol = payload.symbol.strip().upper()
    trade.side = payload.side
    trade.entry_date = payload.entry_date
    trade.entry_quantity = payload.entry_quantity
    trade.entry_price = payload.entry_price
    trade.broker = payload.broker
    trade.notes = payload.notes
    db.commit()
    db.refresh(trade)
    return _trade_out(trade)


@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade(
    trade_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trade = _get_owned_trade(db, user, trade_id)
    if trade.exits:
        raise HTTPException(status_code=409, detail="Trades cannot be deleted after an exit is recorded")
    db.delete(trade)
    db.commit()


@router.post("/{trade_id}/exits", response_model=schemas.TradeOut, status_code=status.HTTP_201_CREATED)
def add_trade_exit(
    trade_id: str,
    payload: schemas.TradeExitIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trade = _get_owned_trade(db, user, trade_id)
    remaining, _, _, _ = _trade_values(trade)
    if payload.quantity > remaining:
        raise HTTPException(status_code=422, detail=f"Exit quantity cannot exceed {float(remaining):g}")
    if payload.exit_date < trade.entry_date:
        raise HTTPException(status_code=422, detail="Exit date cannot be before entry date")
    if "notes" in payload.model_fields_set:
        trade.notes = payload.notes
    db.add(
        models.TradeExit(
            trade_id=trade.id,
            user_id=user.id,
            quantity=payload.quantity,
            exit_price=payload.exit_price,
            exit_date=payload.exit_date,
        )
    )
    db.commit()
    trade = _get_owned_trade(db, user, trade_id)
    return _trade_out(trade)


def update_trade_prices(
    db: Session, user_id: uuid.UUID, prices: dict[str, float], now: datetime
) -> None:
    trades = db.scalars(
        select(models.Trade).where(models.Trade.user_id == user_id)
    ).all()
    for trade in trades:
        remaining, _, _, _ = _trade_values(trade)
        price = prices.get(trade.symbol)
        if remaining > 0 and price is not None:
            trade.current_ltp = price
            trade.last_updated = now


@router.post("/fetch-all", response_model=schemas.TradebookOut)
def fetch_tradebook_prices(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trades = _list_owned_trades(db, user)
    symbols = {trade.symbol for trade in trades if _trade_values(trade)[0] > 0}
    if not symbols:
        return _tradebook_response(trades)
    prices, _, errors = fetch_price_data(symbols)
    if not prices and errors:
        raise HTTPException(status_code=502, detail=f"Could not fetch prices: {next(iter(errors.values()))}")
    update_trade_prices(db, user.id, prices, datetime.now(timezone.utc))
    db.commit()
    return _tradebook_response(_list_owned_trades(db, user))
