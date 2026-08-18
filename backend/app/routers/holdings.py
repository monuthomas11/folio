from datetime import datetime, timezone
import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from yfinance_service import fetch_ltp, fetch_ltps, fetch_sector

from .. import models, schemas
from ..database import get_db
from ..security import get_current_user
from ..services.alerts import evaluate_and_create_alerts

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
    holding = models.Holding(
        user_id=user.id,
        symbol=payload.symbol.strip().upper(),
        quantity=payload.quantity,
        avg_buy_price=payload.avg_buy_price,
        stop_loss=payload.stop_loss,
        target_price=payload.target_price,
        broker=payload.broker,
        sector=payload.sector,
    )
    db.add(holding)
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
    db.delete(holding)
    db.commit()


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
        ltp = fetch_ltp(symbol)
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
        if sector and _missing_sector(holding):
            holding.sector = sector
        holding.last_updated = now
        evaluate_and_create_alerts(db, holding)
    db.commit()

    return schemas.PriceOut(symbol=symbol.strip().upper(), ltp=ltp, last_updated=now)


@router.post("/fetch-all", response_model=list[schemas.HoldingOut])
def fetch_all_prices(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holdings = db.scalars(
        select(models.Holding).where(models.Holding.user_id == user.id)
    ).all()
    if not holdings:
        return []

    symbols = {h.symbol for h in holdings}
    prices, errors = fetch_ltps(symbols)
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
        if holding.symbol in sectors and _missing_sector(holding):
            holding.sector = sectors[holding.symbol]
        holding.last_updated = now
        evaluate_and_create_alerts(db, holding)
    db.commit()

    return db.scalars(
        select(models.Holding)
        .where(models.Holding.user_id == user.id)
        .order_by(models.Holding.created_at.desc())
    ).all()