from datetime import datetime, timezone
import csv
import io
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, selectinload

from yfinance_service import fetch_ltp_with_change, fetch_price_data, fetch_sector

from .. import models, schemas
from ..database import get_db
from ..security import get_current_user
from ..services.alerts import evaluate_and_create_alerts
from ..services.watchlist import update_watchlist_items

router = APIRouter(prefix="/holdings", tags=["holdings"])


def _coerce_uuid(value: str, detail: str = "Holding not found") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


def _get_owned_holding(
    db: Session, user: models.User, holding_id: str
) -> models.Holding:
    holding = db.scalar(
        select(models.Holding).where(
            models.Holding.id == _coerce_uuid(holding_id),
            models.Holding.user_id == user.id,
        )
    )
    if holding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holding not found",
        )
    return holding


def _missing_sector(holding: models.Holding) -> bool:
    return not (holding.sector or "").strip()


def _delete_holding_dependents(
    db: Session, user: models.User, holding: models.Holding
) -> None:
    db.execute(
        delete(models.Recommendation)
        .where(
            or_(
                models.Recommendation.holding_id == holding.id,
                models.Recommendation.run_id.in_(
                    select(models.AnalysisRun.id).where(
                        models.AnalysisRun.holding_id == holding.id,
                        models.AnalysisRun.user_id == user.id,
                    )
                ),
            ),
        )
    )
    db.execute(
        delete(models.AnalysisRun).where(
            models.AnalysisRun.holding_id == holding.id,
        )
    )
    db.execute(
        delete(models.Alert).where(
            models.Alert.holding_id == holding.id,
        )
    )


def _merge_or_create_holding(
    db: Session, user: models.User, payload: schemas.HoldingIn
) -> models.Holding:
    symbol = payload.symbol.strip().upper()
    holding = db.scalar(
        select(models.Holding).where(
            models.Holding.user_id == user.id,
            models.Holding.symbol == symbol,
        )
    )
    if holding is None:
        holding = models.Holding(
            user_id=user.id,
            symbol=symbol,
            quantity=payload.quantity,
            avg_buy_price=payload.avg_buy_price,
            stop_loss=payload.stop_loss,
            target_price=payload.target_price,
            broker=payload.broker,
            sector=payload.sector,
        )
        db.add(holding)
        return holding

    existing_quantity = Decimal(str(holding.quantity))
    new_quantity = Decimal(str(payload.quantity))
    existing_cost = existing_quantity * Decimal(str(holding.avg_buy_price))
    new_cost = new_quantity * Decimal(str(payload.avg_buy_price))
    total_quantity = existing_quantity + new_quantity

    holding.quantity = total_quantity
    holding.avg_buy_price = (existing_cost + new_cost) / total_quantity
    if payload.stop_loss is not None:
        holding.stop_loss = payload.stop_loss
    if payload.target_price is not None:
        holding.target_price = payload.target_price
    if payload.broker is not None:
        holding.broker = payload.broker
    if payload.sector is not None:
        holding.sector = payload.sector
    return holding


@router.get("", response_model=list[schemas.HoldingOut])
def list_holdings(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(models.Holding)
        .where(models.Holding.user_id == user.id)
        .order_by(models.Holding.created_at.desc())
    ).all()


CSV_COLUMNS = [
    "symbol",
    "quantity",
    "avg_buy_price",
    "stop_loss",
    "target_price",
    "broker",
    "sector",
]


@router.get("/export")
def export_holdings(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holdings = db.scalars(
        select(models.Holding).where(models.Holding.user_id == user.id)
    ).all()

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for h in holdings:
        writer.writerow(
            {
                "symbol": h.symbol,
                "quantity": _csv_num(h.quantity),
                "avg_buy_price": _csv_num(h.avg_buy_price),
                "stop_loss": _csv_num(h.stop_loss),
                "target_price": _csv_num(h.target_price),
                "broker": h.broker or "",
                "sector": h.sector or "",
            }
        )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="holdings.csv"',
        },
    )


@router.post("/import", response_model=schemas.ImportResult)
def import_holdings(
    payload: schemas.HoldingsImportIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reader = csv.DictReader(io.StringIO(payload.csv))
    if not reader.fieldnames or "symbol" not in reader.fieldnames:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CSV must have a header row with a symbol column",
        )

    created = 0
    errors: list[schemas.ImportRowError] = []
    for row_number, raw in enumerate(reader, start=2):
        if not any((raw.get(col) or "").strip() for col in CSV_COLUMNS):
            continue
        try:
            holding = models.Holding(
                user_id=user.id,
                symbol=(raw.get("symbol") or "").strip().upper(),
                quantity=float(raw.get("quantity") or 0),
                avg_buy_price=float(raw.get("avg_buy_price") or 0),
                stop_loss=_opt_float(raw.get("stop_loss")),
                target_price=_opt_float(raw.get("target_price")),
                broker=(raw.get("broker") or "").strip() or None,
                sector=(raw.get("sector") or "").strip() or None,
            )
            schemas.HoldingIn(
                symbol=holding.symbol,
                quantity=holding.quantity,
                avg_buy_price=holding.avg_buy_price,
                stop_loss=holding.stop_loss,
                target_price=holding.target_price,
                broker=holding.broker,
                sector=holding.sector,
            )
        except Exception as exc:
            errors.append(
                schemas.ImportRowError(row=row_number, message=_row_error(exc))
            )
            continue
        db.add(holding)
        created += 1

    db.commit()
    return schemas.ImportResult(created=created, errors=errors)


def _row_error(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return f"Invalid value: {exc}"
    return str(exc)


def _opt_float(value: str | None) -> float | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return float(stripped)


def _csv_num(value: float | None) -> str:
    if value is None:
        return ""
    text = f"{float(value):.10f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


@router.post("", response_model=schemas.HoldingOut, status_code=201)
def create_holding(
    payload: schemas.HoldingIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holding = _merge_or_create_holding(db, user, payload)
    db.commit()
    db.refresh(holding)
    return holding


@router.put("/{holding_id}", response_model=schemas.HoldingOut)
def update_holding(
    holding_id: str,
    payload: schemas.HoldingIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holding = _get_owned_holding(db, user, holding_id)
    holding.symbol = payload.symbol.strip().upper()
    holding.quantity = payload.quantity
    holding.avg_buy_price = payload.avg_buy_price
    holding.stop_loss = payload.stop_loss
    holding.target_price = payload.target_price
    holding.broker = payload.broker
    holding.sector = payload.sector
    db.commit()
    db.refresh(holding)
    return holding


@router.delete("/{holding_id}", status_code=204)
def delete_holding(
    holding_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holding = _get_owned_holding(db, user, holding_id)
    _delete_holding_dependents(db, user, holding)
    db.delete(holding)
    db.commit()


@router.get("/exits", response_model=list[schemas.HoldingExitOut])
def list_exits(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(models.HoldingExit)
        .where(models.HoldingExit.user_id == user.id)
        .order_by(models.HoldingExit.exited_at.desc())
    ).all()


@router.post(
    "/{holding_id}/exit",
    response_model=schemas.HoldingExitOut,
    status_code=status.HTTP_201_CREATED,
)
def exit_holding(
    holding_id: str,
    payload: schemas.HoldingExitIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holding = _get_owned_holding(db, user, holding_id)
    quantity = Decimal(str(payload.quantity))
    holding_quantity = Decimal(str(holding.quantity))
    if quantity > holding_quantity:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Exit quantity cannot exceed {float(holding_quantity):g}",
        )

    avg_buy_price = Decimal(str(holding.avg_buy_price))
    exit_price = Decimal(str(payload.exit_price))
    cost_basis = quantity * avg_buy_price
    proceeds = quantity * exit_price
    exit_record = models.HoldingExit(
        user_id=user.id,
        symbol=holding.symbol,
        quantity=quantity,
        avg_buy_price=avg_buy_price,
        exit_price=exit_price,
        cost_basis=cost_basis,
        proceeds=proceeds,
        realized_pnl=proceeds - cost_basis,
        broker=holding.broker,
    )
    db.add(exit_record)

    remaining_quantity = holding_quantity - quantity
    if remaining_quantity == 0:
        _delete_holding_dependents(db, user, holding)
        db.delete(holding)
    else:
        holding.quantity = remaining_quantity

    db.commit()
    db.refresh(exit_record)
    return exit_record


@router.post("/fetch-price/{symbol}", response_model=schemas.PriceOut)
def fetch_price(
    symbol: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holdings = db.scalars(
        select(models.Holding).where(
            models.Holding.user_id == user.id,
            models.Holding.symbol == symbol.strip().upper(),
        )
    ).all()
    if not holdings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No holding with this symbol",
        )

    try:
        ltp, one_day_change_pct = fetch_ltp_with_change(symbol)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch price: {exc}",
        )

    if any(_missing_sector(h) for h in holdings):
        sector = fetch_sector(symbol)
    else:
        sector = None

    now = datetime.now(timezone.utc)
    for holding in holdings:
        holding.current_ltp = ltp
        holding.one_day_change_pct = one_day_change_pct
        if sector and _missing_sector(holding):
            holding.sector = sector
        holding.last_updated = now
        evaluate_and_create_alerts(db, holding)
    watchlist_items = db.scalars(
        select(models.WatchlistItem)
        .options(selectinload(models.WatchlistItem.levels))
        .where(
            models.WatchlistItem.user_id == user.id,
            models.WatchlistItem.symbol == symbol.strip().upper(),
        )
    ).all()
    update_watchlist_items(db, watchlist_items, {symbol.strip().upper(): ltp}, now)
    db.commit()

    return schemas.PriceOut(
        symbol=symbol.strip().upper(),
        ltp=ltp,
        one_day_change_pct=one_day_change_pct,
        last_updated=now,
    )


@router.post("/fetch-all", response_model=list[schemas.HoldingOut])
def fetch_all_prices(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holdings = db.scalars(
        select(models.Holding).where(models.Holding.user_id == user.id)
    ).all()
    watchlist_items = db.scalars(
        select(models.WatchlistItem)
        .options(selectinload(models.WatchlistItem.levels))
        .where(models.WatchlistItem.user_id == user.id)
    ).all()
    if not holdings and not watchlist_items:
        return []

    symbols = {h.symbol for h in holdings} | {item.symbol for item in watchlist_items}
    prices, changes, errors = fetch_price_data(symbols)
    if not prices and errors:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch prices: {next(iter(errors.values()))}",
        )

    missing_sector_symbols = {h.symbol for h in holdings if _missing_sector(h)}
    sectors: dict[str, str] = {}
    for symbol in missing_sector_symbols:
        sector = fetch_sector(symbol)
        if sector:
            sectors[symbol] = sector

    now = datetime.now(timezone.utc)
    for holding in holdings:
        price = prices.get(holding.symbol)
        if price is None:
            continue
        holding.current_ltp = price
        holding.one_day_change_pct = changes.get(holding.symbol)
        if holding.symbol in sectors and _missing_sector(holding):
            holding.sector = sectors[holding.symbol]
        holding.last_updated = now
        evaluate_and_create_alerts(db, holding)
    update_watchlist_items(db, watchlist_items, prices, now)
    db.commit()

    return db.scalars(
        select(models.Holding)
        .where(models.Holding.user_id == user.id)
        .order_by(models.Holding.created_at.desc())
    ).all()
