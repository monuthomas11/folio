from __future__ import annotations

from datetime import datetime, timezone

import yfinance as yf

from ..market_data.yfinance_provider import normalize_symbol
from .base import FundamentalsProvider, FundamentalsSnapshot
from .cache import with_cache


def _num(value: object) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result or result in (float("inf"), float("-inf")):
        return None
    return result


class YFinanceFundamentalsProvider(FundamentalsProvider):
    def get_snapshot(self, symbol: str) -> FundamentalsSnapshot:
        snapshot = with_cache(self._load, symbol)
        assert isinstance(snapshot, FundamentalsSnapshot)
        return snapshot

    def _load(self, symbol: str) -> FundamentalsSnapshot:
        info: dict = {}
        try:
            info = yf.Ticker(normalize_symbol(symbol)).info or {}
        except Exception:
            info = {}
        return FundamentalsSnapshot(
            symbol=symbol.strip().upper(),
            company_name=info.get("longName") or info.get("shortName"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            market_cap=_num(info.get("marketCap")),
            currency=info.get("currency"),
            pe_trailing=_num(info.get("trailingPE")),
            pe_forward=_num(info.get("forwardPE")),
            pb=_num(info.get("priceToBook")),
            ev_to_ebitda=_num(info.get("enterpriseToEbitda")),
            dividend_yield=_num(info.get("dividendYield")),
            peg=_num(info.get("pegRatio")),
            roe=_num(info.get("returnOnEquity")),
            net_profit_margin=_num(info.get("profitMargins")),
            operating_margin=_num(info.get("operatingMargins")),
            revenue_growth=_num(info.get("revenueGrowth")),
            earnings_growth=_num(info.get("earningsGrowth")),
            debt_to_equity=_num(info.get("debtToEquity")),
            current_ratio=_num(info.get("currentRatio")),
            total_cash=_num(info.get("totalCash")),
            total_debt=_num(info.get("totalDebt")),
            free_cashflow=_num(info.get("freeCashflow")),
            operating_cashflow=_num(info.get("operatingCashflow")),
            fifty_two_week_high=_num(info.get("fiftyTwoWeekHigh")),
            fifty_two_week_low=_num(info.get("fiftyTwoWeekLow")),
            beta=_num(info.get("beta")),
            source="yfinance",
            observed_at=datetime.now(timezone.utc),
        )
