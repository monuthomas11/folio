from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel


class FundamentalsSnapshot(BaseModel):
    symbol: str
    company_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    currency: str | None = None
    pe_trailing: float | None = None
    pe_forward: float | None = None
    pb: float | None = None
    ev_to_ebitda: float | None = None
    dividend_yield: float | None = None
    peg: float | None = None
    roe: float | None = None
    net_profit_margin: float | None = None
    operating_margin: float | None = None
    revenue_growth: float | None = None
    earnings_growth: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    total_cash: float | None = None
    total_debt: float | None = None
    free_cashflow: float | None = None
    operating_cashflow: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    beta: float | None = None
    source: str = "yfinance"
    observed_at: datetime | None = None

    def non_null_count(self) -> int:
        fields = [
            self.company_name,
            self.sector,
            self.market_cap,
            self.pe_trailing,
            self.pe_forward,
            self.pb,
            self.ev_to_ebitda,
            self.dividend_yield,
            self.roe,
            self.net_profit_margin,
            self.operating_margin,
            self.revenue_growth,
            self.earnings_growth,
            self.debt_to_equity,
            self.current_ratio,
            self.total_cash,
            self.total_debt,
            self.free_cashflow,
            self.operating_cashflow,
        ]
        return sum(1 for f in fields if f is not None)

    TOTAL_TRACKED_FIELDS: ClassVar[int] = 19


class FundamentalsProvider(ABC):
    @abstractmethod
    def get_snapshot(self, symbol: str) -> FundamentalsSnapshot:
        raise NotImplementedError
