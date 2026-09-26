from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
import uuid

import httpx

from .. import models

NSE_HOME = "https://www.nseindia.com/"
NSE_OPTION_CHAIN = "https://www.nseindia.com/api/option-chain-{}"
NSE_DERIVATIVE_QUOTE = "https://www.nseindia.com/api/quote-derivative"
HEADERS = {
    "accept": "application/json,text/plain,*/*",
    "accept-language": "en-IN,en;q=0.9",
    "user-agent": "Mozilla/5.0 Folio/1.0",
}


def _expiry_matches(value: Any, expiry: date) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() == expiry.strftime("%d-%b-%Y").lower()


def _option_price(payload: dict[str, Any], trade: models.Trade) -> float | None:
    records = payload.get("records") or {}
    rows = records.get("data") or []
    option_key = trade.option_type
    for row in rows:
        if not _expiry_matches(row.get("expiryDate"), trade.expiry_date):
            continue
        try:
            if Decimal(str(row.get("strikePrice"))) != Decimal(str(trade.strike_price)):
                continue
        except (ArithmeticError, TypeError, ValueError):
            continue
        leg = row.get(option_key or "") or {}
        value = leg.get("lastPrice")
        if value is not None and float(value) > 0:
            return float(value)
    return None


def _future_price(payload: dict[str, Any], trade: models.Trade) -> float | None:
    candidates = payload.get("stocks") or payload.get("data") or []
    contract_symbol = (trade.contract_symbol or "").upper()
    for item in candidates:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata") or item
        identifier = str(
            metadata.get("identifier")
            or metadata.get("symbol")
            or item.get("identifier")
            or ""
        ).upper()
        instrument = str(metadata.get("instrumentType") or "").upper()
        if contract_symbol and contract_symbol not in identifier and identifier not in contract_symbol:
            continue
        if instrument and instrument not in {"FUTIDX", "FUTSTK"}:
            continue
        if trade.expiry_date and not _expiry_matches(
            metadata.get("expiryDate") or item.get("expiryDate"), trade.expiry_date
        ):
            continue
        trade_info = (item.get("marketDeptOrderBook") or {}).get("tradeInfo") or {}
        value = trade_info.get("lastPrice") or metadata.get("lastPrice") or item.get("lastPrice")
        if value is not None and float(value) > 0:
            return float(value)
    return None


def _fetch_trade_price(client: httpx.Client, trade: models.Trade) -> float:
    if not trade.underlying_symbol or not trade.expiry_date:
        raise ValueError("Contract metadata is incomplete")
    symbol = trade.underlying_symbol.upper()
    if trade.instrument_type == "option":
        endpoint = "indices" if trade.underlying_type == "index" else "equities"
        response = client.get(
            NSE_OPTION_CHAIN.format(endpoint), params={"symbol": symbol}
        )
        response.raise_for_status()
        value = _option_price(response.json(), trade)
    else:
        response = client.get(NSE_DERIVATIVE_QUOTE, params={"symbol": symbol})
        response.raise_for_status()
        value = _future_price(response.json(), trade)
    if value is None:
        raise ValueError("No live quote was found for this contract")
    return value


def fetch_fno_prices(
    trades: list[models.Trade],
) -> tuple[dict[uuid.UUID, float], dict[uuid.UUID, str]]:
    prices: dict[uuid.UUID, float] = {}
    errors: dict[uuid.UUID, str] = {}
    supported_trades = []
    for trade in trades:
        if trade.exchange != "NSE":
            errors[trade.id] = "Live F&O quotes are unavailable for this exchange; record a manual mark"
        else:
            supported_trades.append(trade)
    if not supported_trades:
        return prices, errors
    try:
        with httpx.Client(
            headers=HEADERS, timeout=10.0, follow_redirects=True
        ) as client:
            client.get(NSE_HOME)
            for trade in supported_trades:
                try:
                    prices[trade.id] = _fetch_trade_price(client, trade)
                except Exception as exc:
                    errors[trade.id] = str(exc)
    except Exception as exc:
        for trade in supported_trades:
            errors[trade.id] = str(exc)
    return prices, errors
