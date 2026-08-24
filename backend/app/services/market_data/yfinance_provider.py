from __future__ import annotations

import yfinance as yf

from yfinance_service import fetch_ltp as _fetch_ltp_legacy

from .base import MarketDataProvider, NewsItem, OHLCV

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

    def get_news(self, symbol: str, limit: int = 6) -> list[NewsItem]:
        try:
            ticker = yf.Ticker(normalize_symbol(symbol))
            raw = ticker.news
        except Exception:
            return []
        if not isinstance(raw, list):
            return []
        items: list[NewsItem] = []
        for entry in raw[:limit]:
            if not isinstance(entry, dict):
                continue
            title = entry.get("title")
            if not title:
                continue
            content = entry.get("content")
            summary = None
            if isinstance(content, dict):
                summary = content.get("summary") or content.get("description")
            items.append(
                NewsItem(
                    title=str(title),
                    publisher=(
                        str(entry["publisher"]) if entry.get("publisher") else None
                    ),
                    link=entry.get("link"),
                    published_at=(
                        entry.get("providerPublishTime")
                        or entry.get("provider_publish_time")
                    ),
                    summary=str(summary) if summary else None,
                )
            )
        return items
