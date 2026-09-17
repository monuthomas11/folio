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
    return _read_price_data(ticker, symbol)[0]


def _read_price_data(ticker: yf.Ticker, symbol: str) -> tuple[float, float | None]:
    info = ticker.fast_info
    last = getattr(info, "last_price", None)
    if last is not None and last > 0:
        last = float(last)
        previous = getattr(info, "previous_close", None)
        if previous is not None and previous > 0:
            return last, (last - float(previous)) / float(previous) * 100
    else:
        last = None

    hist = ticker.history(period="5d")
    if hist.empty:
        raise ValueError(f"No price data for {symbol}")
    closes = hist["Close"].dropna()
    if closes.empty:
        raise ValueError(f"No price data for {symbol}")
    last = last or float(closes.iloc[-1])
    previous = float(closes.iloc[-2]) if len(closes) > 1 else None
    change = (last - previous) / previous * 100 if previous and previous > 0 else None
    return last, change


def fetch_ltp(symbol: str) -> float:
    ticker = yf.Ticker(_normalize(symbol))
    return _read_ltp(ticker, symbol)


def fetch_ltp_with_change(symbol: str) -> tuple[float, float | None]:
    ticker = yf.Ticker(_normalize(symbol))
    return _read_price_data(ticker, symbol)


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


def fetch_price_data(
    symbols: Iterable[str],
) -> tuple[dict[str, float], dict[str, float | None], dict[str, str]]:
    prices: dict[str, float] = {}
    changes: dict[str, float | None] = {}
    errors: dict[str, str] = {}
    for symbol in symbols:
        try:
            price, change = fetch_ltp_with_change(symbol)
            prices[symbol] = price
            changes[symbol] = change
        except Exception as exc:
            errors[symbol] = str(exc)
    return prices, changes, errors
