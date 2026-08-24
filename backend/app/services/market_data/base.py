from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from pydantic import BaseModel


class OHLCV(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class NewsItem(BaseModel):
    title: str
    publisher: str | None = None
    link: str | None = None
    published_at: str | None = None
    summary: str | None = None


class MarketDataProvider(ABC):
    @abstractmethod
    def get_ltp(self, symbol: str) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_ohlcv(self, symbol: str, period: str = "1y") -> list[OHLCV]:
        raise NotImplementedError

    def get_news(self, symbol: str, limit: int = 6) -> list[NewsItem]:
        return []
