from __future__ import annotations

from typing import Iterable

import yfinance as yf

NSE_SUFFIX = ".NS"


def _normalize(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not symbol.endswith((NSE_SUFFIX, ".BO")):
        symbol += NSE_SUFFIX
    return symbol


def _read_ltp(ticker: yf.Ticker, symbol: str) -> float:
    info = ticker.fast_info
    last = getattr(info, "last_price", None)
    if last is not None and last > 0:
        return float(last)

    hist = ticker.history(period="1d")
    if hist.empty:
        raise ValueError(f"No price data for {symbol}")
    return float(hist["Close"].iloc[-1])


def fetch_ltp(symbol: str) -> float:
    ticker = yf.Ticker(_normalize(symbol))
    return _read_ltp(ticker, symbol)


def fetch_sector(symbol: str) -> str | None:
    try:
        ticker = yf.Ticker(_normalize(symbol))
        sector = ticker.info.get("sector")
    except Exception:
        return None
    if sector is None:
        return None
    sector = str(sector).strip()
    return sector or None


def fetch_ltps(
    symbols: Iterable[str],
) -> tuple[dict[str, float], dict[str, str]]:
    prices: dict[str, float] = {}
    errors: dict[str, str] = {}
    for symbol in symbols:
        try:
            prices[symbol] = fetch_ltp(symbol)
        except Exception as exc:
            errors[symbol] = str(exc)
    return prices, errors