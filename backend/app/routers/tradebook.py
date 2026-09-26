from datetime import datetime, timezone
from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from yfinance_service import fetch_price_data

from .. import models, schemas
from ..database import get_db
from ..security import get_current_user
from ..services.fno_quotes import fetch_fno_prices
from ..services.tradebook_calculations import (
    calculate_summary,
    calculate_trade,
    entry_units,
    remaining_units,
)

router = APIRouter(prefix="/tradebook", tags=["tradebook"])


def _coerce_uuid(value: str, detail: str = "Trade not found") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=404, detail=detail)


def _trade_options():
    return (
        selectinload(models.Trade.exits).selectinload(models.TradeExit.charges),
        selectinload(models.Trade.charges),
    )


def _get_owned_trade(db: Session, user: models.User, trade_id: str) -> models.Trade:
    trade = db.scalar(
        select(models.Trade)
        .options(*_trade_options())
        .where(
            models.Trade.id == _coerce_uuid(trade_id),
            models.Trade.user_id == user.id,
        )
    )
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


def _asset_filter(asset_class: str):
    if asset_class == "equity":
        return or_(
            models.Trade.asset_class == "equity",
            models.Trade.asset_class.is_(None),
        )
    return models.Trade.asset_class == asset_class


def _list_owned_trades(
    db: Session, user: models.User, asset_class: str | None = None
) -> list[models.Trade]:
    query = (
        select(models.Trade)
        .options(*_trade_options())
        .where(models.Trade.user_id == user.id)
    )
    if asset_class:
        query = query.where(_asset_filter(asset_class))
    query = query.order_by(models.Trade.entry_date.desc(), models.Trade.created_at.desc())
    return list(db.scalars(query).all())


def _upsert_charge(
    db: Session,
    user: models.User,
    trade: models.Trade,
    payload: schemas.TradeChargesIn | None,
    leg_type: str,
    trade_exit: models.TradeExit | None = None,
) -> None:
    if payload is None:
        return
    charge = None
    for candidate in trade.charges:
        if candidate.leg_type != leg_type:
            continue
        if leg_type == "entry" and candidate.trade_exit_id is None:
            charge = candidate
            break
        if leg_type == "exit" and trade_exit is not None and candidate.trade_exit_id == trade_exit.id:
            charge = candidate
            break
    values = payload.model_dump()
    if charge is None:
        charge = models.TradeCharge(
            user_id=user.id,
            trade_id=trade.id,
            trade_exit_id=trade_exit.id if trade_exit else None,
            leg_type=leg_type,
            **values,
        )
        db.add(charge)
        trade.charges.append(charge)
    else:
        for key, value in values.items():
            setattr(charge, key, value)


def _apply_trade_payload(trade: models.Trade, payload: schemas.TradeIn) -> None:
    trade.symbol = payload.symbol.strip().upper()
    trade.side = payload.side
    trade.asset_class = payload.asset_class
    trade.instrument_type = payload.instrument_type
    trade.exchange = payload.exchange
    trade.underlying_type = payload.underlying_type
    trade.underlying_symbol = (
        payload.underlying_symbol.strip().upper()
        if payload.underlying_symbol
        else None
    )
    trade.contract_symbol = payload.contract_symbol.strip().upper() if payload.contract_symbol else None
    trade.expiry_date = payload.expiry_date
    trade.strike_price = payload.strike_price
    trade.tick_size = payload.tick_size
    trade.option_type = payload.option_type
    trade.lot_size = payload.lot_size
    trade.entry_lots = payload.entry_lots
    trade.product_type = payload.product_type
    trade.entry_at = payload.entry_at
    trade.entry_order_id = payload.entry_order_id
    trade.entry_contract_note_ref = payload.entry_contract_note_ref
    trade.strategy = payload.strategy
    trade.thesis = payload.thesis
    trade.settlement_type = payload.settlement_type
    trade.margin_used = payload.margin_used
    trade.entry_date = payload.entry_date
    trade.entry_quantity = (
        float(payload.entry_lots * payload.lot_size)
        if payload.asset_class == "fno"
        else payload.entry_quantity
    )
    trade.entry_price = payload.entry_price
    trade.broker = payload.broker
    trade.notes = payload.notes


def _validate_exit(trade: models.Trade, payload: schemas.TradeExitIn) -> Decimal:
    if payload.exit_date < trade.entry_date:
        raise HTTPException(status_code=422, detail="Exit date cannot be before entry date")
    if (trade.asset_class or "equity") == "fno":
        if payload.exit_lots is None:
            raise HTTPException(status_code=422, detail="F&O exits require whole lots")
        if payload.quantity is not None:
            expected_quantity = Decimal(payload.exit_lots * (trade.lot_size or 0))
            if Decimal(str(payload.quantity)) != expected_quantity:
                raise HTTPException(status_code=422, detail="Exit quantity must equal lots multiplied by lot size")
        quantity = Decimal(payload.exit_lots * (trade.lot_size or 0))
    else:
        if payload.quantity is None:
            raise HTTPException(status_code=422, detail="Equity exits require quantity")
        quantity = Decimal(str(payload.quantity))
    remaining = remaining_units(trade)
    if quantity > remaining:
        raise HTTPException(
            status_code=422,
            detail=f"Exit quantity cannot exceed {float(remaining):g}",
        )
    return quantity


def _tradebook_response(
    trades: list[models.Trade], quote_errors: list[dict] | None = None
) -> dict:
    calculations = [calculate_trade(trade) for trade in trades]
    return {
        "summary": calculate_summary(calculations),
        "trades": [calculation.row for calculation in calculations],
        "quote_errors": quote_errors or [],
    }


@router.get("", response_model=schemas.TradebookOut)
def get_tradebook(
    asset_class: schemas.AssetClass = Query("equity", alias="assetClass"),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _tradebook_response(_list_owned_trades(db, user, asset_class))


@router.post("", response_model=schemas.TradeOut, status_code=status.HTTP_201_CREATED)
def create_trade(
    payload: schemas.TradeIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trade = models.Trade(user_id=user.id)
    _apply_trade_payload(trade, payload)
    db.add(trade)
    db.flush()
    _upsert_charge(db, user, trade, payload.entry_charges, "entry")
    db.commit()
    return _trade_out_after_commit(db, user, trade.id)


def _trade_out_after_commit(db: Session, user: models.User, trade_id: uuid.UUID) -> dict:
    trade = _get_owned_trade(db, user, str(trade_id))
    return calculate_trade(trade).row


@router.put("/{trade_id}", response_model=schemas.TradeOut)
def update_trade(
    trade_id: str,
    payload: schemas.TradeIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trade = _get_owned_trade(db, user, trade_id)
    if trade.exits:
        raise HTTPException(
            status_code=409,
            detail="Trades cannot be edited after an exit is recorded",
        )
    _apply_trade_payload(trade, payload)
    _upsert_charge(db, user, trade, payload.entry_charges, "entry")
    db.commit()
    return _trade_out_after_commit(db, user, trade.id)


@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade(
    trade_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trade = _get_owned_trade(db, user, trade_id)
    if trade.exits:
        raise HTTPException(
            status_code=409,
            detail="Trades cannot be deleted after an exit is recorded",
        )
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
    quantity = _validate_exit(trade, payload)
    exit_record = models.TradeExit(
        trade_id=trade.id,
        user_id=user.id,
        quantity=float(quantity),
        exit_lots=payload.exit_lots,
        exit_price=payload.exit_price,
        exit_date=payload.exit_date,
        exit_at=payload.exit_at,
        exit_reason=payload.exit_reason,
        exit_order_id=payload.exit_order_id,
        exit_contract_note_ref=payload.exit_contract_note_ref,
        notes=payload.notes,
    )
    db.add(exit_record)
    db.flush()
    _upsert_charge(db, user, trade, payload.charges, "exit", exit_record)
    if "notes" in payload.model_fields_set:
        trade.notes = payload.notes
    db.commit()
    return _trade_out_after_commit(db, user, trade.id)


@router.put("/{trade_id}/mark", response_model=schemas.TradeOut)
def update_trade_mark(
    trade_id: str,
    payload: schemas.TradeMarkIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trade = _get_owned_trade(db, user, trade_id)
    if remaining_units(trade) <= 0:
        raise HTTPException(status_code=409, detail="Closed trades cannot receive a new mark")
    trade.current_ltp = payload.ltp
    trade.mark_source = payload.source
    trade.last_updated = datetime.now(timezone.utc)
    db.commit()
    return _trade_out_after_commit(db, user, trade.id)


@router.put("/{trade_id}/charges", response_model=schemas.TradeOut)
def update_entry_charges(
    trade_id: str,
    payload: schemas.TradeChargesIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trade = _get_owned_trade(db, user, trade_id)
    _upsert_charge(db, user, trade, payload, "entry")
    db.commit()
    return _trade_out_after_commit(db, user, trade.id)


@router.put("/{trade_id}/exits/{exit_id}/charges", response_model=schemas.TradeOut)
def update_exit_charges(
    trade_id: str,
    exit_id: str,
    payload: schemas.TradeChargesIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trade = _get_owned_trade(db, user, trade_id)
    exit_uuid = _coerce_uuid(exit_id, "Exit not found")
    exit_record = next((item for item in trade.exits if item.id == exit_uuid), None)
    if exit_record is None:
        raise HTTPException(status_code=404, detail="Exit not found")
    _upsert_charge(db, user, trade, payload, "exit", exit_record)
    db.commit()
    return _trade_out_after_commit(db, user, trade.id)


def update_trade_prices(
    db: Session, user_id: uuid.UUID, prices: dict[str, float], now: datetime
) -> None:
    trades = db.scalars(
        select(models.Trade).where(
            models.Trade.user_id == user_id,
            or_(models.Trade.asset_class == "equity", models.Trade.asset_class.is_(None)),
        )
    ).all()
    for trade in trades:
        if remaining_units(trade) <= 0:
            continue
        price = prices.get(trade.symbol)
        if price is not None:
            trade.current_ltp = price
            trade.mark_source = "exchange"
            trade.last_updated = now


@router.post("/fetch-all", response_model=schemas.TradebookOut)
def fetch_tradebook_prices(
    asset_class: schemas.AssetClass = Query("equity", alias="assetClass"),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trades = _list_owned_trades(db, user, asset_class)
    open_trades = [trade for trade in trades if remaining_units(trade) > 0]
    now = datetime.now(timezone.utc)
    quote_errors: list[dict] = []
    if asset_class == "fno":
        prices, errors = fetch_fno_prices(open_trades)
        for trade in open_trades:
            price = prices.get(trade.id)
            if price is not None:
                trade.current_ltp = price
                trade.mark_source = "exchange"
                trade.last_updated = now
            elif trade.id in errors:
                quote_errors.append(
                    {
                        "trade_id": trade.id,
                        "symbol": trade.symbol,
                        "message": errors[trade.id],
                    }
                )
    else:
        symbols = {trade.symbol for trade in open_trades}
        if symbols:
            prices, _, errors = fetch_price_data(symbols)
            for trade in open_trades:
                price = prices.get(trade.symbol)
                if price is not None:
                    trade.current_ltp = price
                    trade.mark_source = "exchange"
                    trade.last_updated = now
                elif trade.symbol in errors:
                    quote_errors.append(
                        {
                            "trade_id": trade.id,
                            "symbol": trade.symbol,
                            "message": errors[trade.symbol],
                        }
                    )
    db.commit()
    return _tradebook_response(_list_owned_trades(db, user, asset_class), quote_errors)
