from __future__ import annotations

import yfinance as yf

from yfinance_service import fetch_ltp as _fetch_ltp_legacy

from .base import MarketDataProvider, OHLCV

NSE_SUFFIX = ".NS"


def normalize_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not symbol.endswith((NSE_SUFFIX, ".BO")):
        symbol += NSE_SUFFIX
    return symbol


class YFinanceMarketDataProvider(MarketDataProvider):
    def get_ltp(self, symbol: str) -> float:
        return _fetch_ltp_legacy(symbol)

    def get_ohlcv(self, symbol: str, period: str = "1y") -> list[OHLCV]:
        ticker = yf.Ticker(normalize_symbol(symbol))
        hist = ticker.history(period=period)
        bars: list[OHLCV] = []
        for idx, row in hist.iterrows():
            close = row.get("Close")
            if close is None or close != close:
                continue
            bars.append(
                OHLCV(
                    date=idx.date(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(close),
                    volume=float(row.get("Volume") or 0),
                )
            )
        return bars
