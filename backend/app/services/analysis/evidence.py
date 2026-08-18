from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel

FRESH_MINUTES = 60
RECENT_MINUTES = 60 * 24


def freshness_label(observed_at: datetime | None) -> str:
    if observed_at is None:
        return "unknown"
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    age_minutes = (datetime.now(timezone.utc) - observed_at).total_seconds() / 60.0
    if age_minutes <= FRESH_MINUTES:
        return "FRESH"
    if age_minutes <= RECENT_MINUTES:
        return "RECENT"
    return "STALE"


class EvidenceItem(BaseModel):
    id: str
    category: str
    label: str
    value: object
    unit: str | None = None
    source: str
    observed_at: str | None = None
    freshness: str = "unknown"
    confidence: str = "MEDIUM"
    note: str | None = None


class DataQuality(BaseModel):
    score: int
    grade: str
    completeness_pct: float
    gates: list[str]


def _grade(score: int) -> str:
    if score >= 80:
        return "EXCELLENT"
    if score >= 60:
        return "GOOD"
    if score >= 40:
        return "MODERATE"
    return "POOR"


class EvidenceBuilder:
    def __init__(self) -> None:
        self._items: list[EvidenceItem] = []

    def add(
        self,
        category: str,
        label: str,
        value: object,
        source: str,
        observed_at: datetime | None = None,
        unit: str | None = None,
        confidence: str = "MEDIUM",
        note: str | None = None,
    ) -> EvidenceItem | None:
        if value is None:
            return None
        item = EvidenceItem(
            id=f"E{len(self._items) + 1:03d}",
            category=category,
            label=label,
            value=value,
            unit=unit,
            source=source,
            observed_at=observed_at.isoformat() if observed_at else None,
            freshness=freshness_label(observed_at),
            confidence=confidence,
            note=note,
        )
        self._items.append(item)
        return item

    @property
    def items(self) -> list[EvidenceItem]:
        return self._items

    @property
    def ids(self) -> list[str]:
        return [item.id for item in self._items]


def build_position_evidence(
    builder: EvidenceBuilder,
    holding,
    portfolio_total_value: float,
    holding_count: int,
) -> dict:
    qty = float(holding.quantity)
    avg_price = float(holding.avg_buy_price)
    invested = qty * avg_price
    ltp = float(holding.current_ltp) if holding.current_ltp is not None else None
    current_value = qty * ltp if ltp is not None else None
    pnl = (current_value - invested) if current_value is not None else None
    pnl_pct = (pnl / invested * 100.0) if (pnl is not None and invested) else None
    weight = (
        current_value / portfolio_total_value * 100.0
        if (current_value is not None and portfolio_total_value > 0)
        else None
    )

    observed = holding.last_updated
    builder.add(
        "position", "Quantity", qty, "user-input", None, unit="shares", confidence="HIGH"
    )
    builder.add(
        "position",
        "Average buy price",
        round(avg_price, 2),
        "user-input",
        None,
        unit="INR",
        confidence="HIGH",
    )
    builder.add(
        "position", "Invested amount", round(invested, 2), "user-input", None, unit="INR",
        confidence="HIGH",
    )
    builder.add(
        "position", "Current LTP", ltp, "yfinance", observed, unit="INR", confidence="HIGH"
    )
    builder.add(
        "position",
        "Current value",
        round(current_value, 2) if current_value is not None else None,
        "computed",
        observed,
        unit="INR",
    )
    builder.add(
        "position",
        "Unrealised P/L",
        round(pnl, 2) if pnl is not None else None,
        "computed",
        observed,
        unit="INR",
    )
    builder.add(
        "position",
        "Unrealised P/L %",
        round(pnl_pct, 2) if pnl_pct is not None else None,
        "computed",
        observed,
        unit="pct",
    )
    builder.add(
        "portfolio",
        "Portfolio weight",
        round(weight, 2) if weight is not None else None,
        "computed",
        observed,
        unit="pct",
    )
    builder.add(
        "position",
        "Stop loss",
        float(holding.stop_loss) if holding.stop_loss is not None else None,
        "user-input",
        None,
        unit="INR",
        confidence="HIGH",
    )
    builder.add(
        "position",
        "Target price",
        float(holding.target_price) if holding.target_price is not None else None,
        "user-input",
        None,
        unit="INR",
        confidence="HIGH",
    )

    distance = {}
    if ltp is not None and ltp > 0:
        if holding.stop_loss is not None:
            distance["distance_to_stop_loss_pct"] = round(
                (ltp - float(holding.stop_loss)) / ltp * 100.0, 2
            )
        if holding.target_price is not None:
            distance["distance_to_target_pct"] = round(
                (float(holding.target_price) - ltp) / ltp * 100.0, 2
            )
        distance["distance_to_avg_buy_pct"] = round(
            (ltp - avg_price) / ltp * 100.0, 2
        )

    return {
        "symbol": holding.symbol,
        "quantity": qty,
        "avg_buy_price": avg_price,
        "invested": round(invested, 2),
        "current_ltp": ltp,
        "current_value": round(current_value, 2) if current_value is not None else None,
        "pnl": round(pnl, 2) if pnl is not None else None,
        "pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
        "portfolio_weight_pct": round(weight, 2) if weight is not None else None,
        "stop_loss": holding.stop_loss,
        "target_price": holding.target_price,
        "broker": holding.broker,
        "sector": holding.sector,
        "distance": distance,
        "holding_count": holding_count,
    }


def build_technical_evidence(builder: EvidenceBuilder, tech) -> dict | None:
    if tech is None or tech.insufficient_data:
        builder.add(
            "technical",
            "Technical data availability",
            "insufficient (fewer than 60 price bars)",
            "computed",
            None,
            confidence="LOW",
            note="Technical analysis cannot be computed reliably.",
        )
        return None
    observed = tech.computed_at
    src = "computed"
    items = [
        ("Close", tech.close, "INR"),
        ("EMA 20", round(tech.ema20, 2) if tech.ema20 else None, "INR"),
        ("EMA 50", round(tech.ema50, 2) if tech.ema50 else None, "INR"),
        ("EMA 200", round(tech.ema200, 2) if tech.ema200 else None, "INR"),
        ("RSI 14", round(tech.rsi14, 1) if tech.rsi14 is not None else None, None),
        ("MACD histogram", tech.macd_histogram, None),
        ("MACD direction", tech.macd_direction, None),
        ("ATR 14", round(tech.atr14, 2) if tech.atr14 is not None else None, "INR"),
        ("ATR pct of price", round(tech.atr_pct, 2) if tech.atr_pct is not None else None, "pct"),
        ("52-week high", tech.high_52w, "INR"),
        ("52-week low", tech.low_52w, "INR"),
        (
            "Distance to 52w high",
            round(tech.distance_to_52w_high_pct, 2)
            if tech.distance_to_52w_high_pct is not None
            else None,
            "pct",
        ),
        (
            "Distance to 52w low",
            round(tech.distance_to_52w_low_pct, 2)
            if tech.distance_to_52w_low_pct is not None
            else None,
            "pct",
        ),
        ("Volume trend (20d vs 60d avg)", tech.volume_trend, None),
    ]
    for label, value, unit in items:
        builder.add("technical", label, value, src, observed, unit=unit)
    for label, value in (
        ("Long-term trend", tech.long_term_trend),
        ("Medium-term trend", tech.medium_term_trend),
        ("Short-term trend", tech.short_term_trend),
        ("Momentum", tech.momentum),
        ("Volatility band", tech.volatility),
        ("Overall trend score (0-100)", tech.overall_trend_score),
    ):
        builder.add("technical", label, value, src, observed)
    return tech.model_dump(exclude={"symbol", "insufficient_data"}, exclude_none=False)


def build_fundamental_evidence(builder: EvidenceBuilder, fund):
    if fund is None:
        builder.add(
            "fundamental",
            "Fundamentals availability",
            "unavailable",
            "yfinance",
            None,
            confidence="LOW",
            note="No fundamental data could be retrieved.",
        )
        return None
    observed = fund.observed_at
    src = fund.source or "yfinance"
    rows = [
        ("Company name", fund.company_name, None, "MEDIUM"),
        ("Sector", fund.sector, None, "MEDIUM"),
        ("Industry", fund.industry, None, "MEDIUM"),
        ("Market cap", fund.market_cap, fund.currency or "currency", "MEDIUM"),
        ("Trailing P/E", fund.pe_trailing, None, "MEDIUM"),
        ("Forward P/E", fund.pe_forward, None, "MEDIUM"),
        ("P/B", fund.pb, None, "MEDIUM"),
        ("EV/EBITDA", fund.ev_to_ebitda, None, "MEDIUM"),
        ("Dividend yield", fund.dividend_yield, "pct", "MEDIUM"),
        ("ROE", fund.roe, "pct", "MEDIUM"),
        ("Net profit margin", fund.net_profit_margin, "pct", "MEDIUM"),
        ("Operating margin", fund.operating_margin, "pct", "MEDIUM"),
        ("Revenue growth YoY", fund.revenue_growth, "pct", "MEDIUM"),
        ("Earnings growth YoY", fund.earnings_growth, "pct", "MEDIUM"),
        ("Debt to equity", fund.debt_to_equity, None, "MEDIUM"),
        ("Current ratio", fund.current_ratio, None, "MEDIUM"),
        ("Total cash", fund.total_cash, fund.currency or "currency", "MEDIUM"),
        ("Total debt", fund.total_debt, fund.currency or "currency", "MEDIUM"),
        ("Free cash flow", fund.free_cashflow, fund.currency or "currency", "MEDIUM"),
        ("Operating cash flow", fund.operating_cashflow, fund.currency or "currency", "MEDIUM"),
        ("52-week high", fund.fifty_two_week_high, fund.currency or "INR", "HIGH"),
        ("52-week low", fund.fifty_two_week_low, fund.currency or "INR", "HIGH"),
        ("Beta", fund.beta, None, "MEDIUM"),
    ]
    for label, value, unit, confidence in rows:
        builder.add("fundamental", label, value, src, observed, unit=unit, confidence=confidence)
    return fund.model_dump(exclude={"symbol"}, exclude_none=False)


def build_portfolio_context(
    builder: EvidenceBuilder, holdings, profile
) -> dict:
    total_value = 0.0
    sector_value: dict[str, float] = {}
    for h in holdings:
        if h.current_ltp is None:
            continue
        value = float(h.quantity) * float(h.current_ltp)
        total_value += value
        sector = (h.sector or "Unclassified").strip() or "Unclassified"
        sector_value[sector] = sector_value.get(sector, 0.0) + value

    warnings = []
    for h in holdings:
        if h.current_ltp is None or total_value <= 0:
            continue
        weight = float(h.quantity) * float(h.current_ltp) / total_value * 100.0
        if weight >= float(profile.max_single_stock_weight):
            warnings.append(
                {
                    "type": "stock_concentration",
                    "symbol": h.symbol,
                    "weight_pct": round(weight, 2),
                    "limit_pct": float(profile.max_single_stock_weight),
                }
            )
            builder.add(
                "portfolio",
                f"Concentration flag: {h.symbol}",
                f"weight {round(weight, 2)}% exceeds limit {profile.max_single_stock_weight}%",
                "computed",
                h.last_updated,
                confidence="HIGH",
            )

    sector_weights = []
    for sector, value in sorted(sector_value.items(), key=lambda kv: -kv[1]):
        weight = round(value / total_value * 100.0, 2) if total_value else 0.0
        sector_weights.append({"sector": sector, "weight_pct": weight})
        if weight >= float(profile.max_sector_weight):
            warnings.append(
                {
                    "type": "sector_concentration",
                    "sector": sector,
                    "weight_pct": weight,
                    "limit_pct": float(profile.max_sector_weight),
                }
            )
    builder.add(
        "portfolio",
        "Sector weights",
        sector_weights,
        "computed",
        datetime.now(timezone.utc),
        confidence="MEDIUM",
    )

    return {
        "total_value": round(total_value, 2),
        "holding_count": len(holdings),
        "sector_weights": sector_weights,
        "concentration_warnings": warnings,
        "has_stale_prices": any(h.last_updated is None for h in holdings)
        or any(
            (h.last_updated and freshness_label(h.last_updated) == "STALE")
            for h in holdings
        ),
    }


def compute_data_quality(
    builder: EvidenceBuilder, fund, tech, ltp_observed_at: datetime | None
) -> tuple[DataQuality, str]:
    flags: list[str] = []
    score = 60.0

    completeness_fields = [
        fund.company_name if fund else None,
        fund.sector if fund else None,
        fund.market_cap if fund else None,
        fund.pe_trailing if fund else None,
        fund.pe_forward if fund else None,
        fund.pb if fund else None,
        fund.ev_to_ebitda if fund else None,
        fund.dividend_yield if fund else None,
        fund.roe if fund else None,
        fund.net_profit_margin if fund else None,
        fund.operating_margin if fund else None,
        fund.revenue_growth if fund else None,
        fund.earnings_growth if fund else None,
        fund.debt_to_equity if fund else None,
        fund.current_ratio if fund else None,
        fund.total_cash if fund else None,
        fund.total_debt if fund else None,
        fund.free_cashflow if fund else None,
        fund.operating_cashflow if fund else None,
        tech.close if tech and not tech.insufficient_data else None,
        tech.rsi14 if tech and not tech.insufficient_data else None,
    ]
    present = sum(1 for v in completeness_fields if v is not None)
    completeness = present / len(completeness_fields)
    score = completeness * 50.0

    ltp_freshness = freshness_label(ltp_observed_at)
    if ltp_freshness == "FRESH":
        score += 25.0
    elif ltp_freshness == "RECENT":
        score += 15.0
    else:
        score += 0.0

    stale_fundamental = fund is not None and fund.observed_at is not None and (
        datetime.now(timezone.utc) - fund.observed_at
    ).total_seconds() > 60 * 60 * 12
    if stale_fundamental:
        score -= 5.0

    if tech is not None and not tech.insufficient_data:
        score += 10.0
    else:
        score -= 10.0

    if fund is None or completeness < 0.4:
        flags.append("LOW_CONFIDENCE")
    if ltp_freshness == "STALE":
        flags.append("STALE_DATA")
    if stale_fundamental:
        flags.append("STALE_DATA")
    source_count = {"yfinance"}
    if len(source_count) < 2:
        score -= 10.0
        flags.append("LOW_SOURCE_CONFIDENCE")

    score = int(max(0, min(100, round(score))))
    quality = DataQuality(
        score=score,
        grade=_grade(score),
        completeness_pct=round(completeness * 100.0, 1),
        gates=flags,
    )
    return quality, ltp_freshness


def build_evidence_pack(
    holding,
    holdings,
    tech,
    fund,
    profile,
):
    builder = EvidenceBuilder()

    total_value = 0.0
    for h in holdings:
        if h.current_ltp is not None:
            total_value += float(h.quantity) * float(h.current_ltp)

    position = build_position_evidence(builder, holding, total_value, len(holdings))
    technical = build_technical_evidence(builder, tech)
    fundamental = build_fundamental_evidence(builder, fund)
    portfolio_context = build_portfolio_context(builder, holdings, profile)

    quality, ltp_freshness = compute_data_quality(
        builder, fund, tech, holding.last_updated
    )
    if "PORTFOLIO_CONCENTRATION" not in quality.gates:
        if portfolio_context["concentration_warnings"]:
            quality.gates.append("PORTFOLIO_CONCENTRATION")

    pack = {
        "security": {
            "symbol": holding.symbol,
            "sector": holding.sector,
            "broker": holding.broker,
        },
        "position": position,
        "fundamentals": fundamental,
        "valuation": fundamental,
        "technical": technical,
        "portfolio_context": portfolio_context,
        "investment_profile": {
            "investment_style": profile.investment_style,
            "risk_tolerance": profile.risk_tolerance,
            "investment_horizon": profile.investment_horizon,
            "max_single_stock_weight_pct": float(profile.max_single_stock_weight),
            "max_sector_weight_pct": float(profile.max_sector_weight),
            "warn_single_stock_weight_pct": float(profile.warn_single_stock_weight),
            "warn_sector_weight_pct": float(profile.warn_sector_weight),
        },
        "evidence": [item.model_dump() for item in builder.items],
        "data_quality": {
            "score": quality.score,
            "grade": quality.grade,
            "completeness_pct": quality.completeness_pct,
            "gates": quality.gates,
        },
    }
    return pack, builder, quality
