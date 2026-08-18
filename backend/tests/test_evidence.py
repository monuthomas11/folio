from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.analysis.evidence import (
    EvidenceBuilder,
    build_evidence_pack,
    build_position_evidence,
    freshness_label,
)
from app.services.fundamentals.base import FundamentalsSnapshot
from app.services.technicals.indicators import TechnicalSnapshot


def _holding(**overrides):
    data = {
        "symbol": "RELIANCE",
        "quantity": 10,
        "avg_buy_price": 100.0,
        "stop_loss": 90.0,
        "target_price": 130.0,
        "broker": "Zerodha",
        "sector": "Energy",
        "current_ltp": 110.0,
        "last_updated": datetime.now(timezone.utc),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _profile(**overrides):
    data = {
        "investment_style": "Moderate",
        "risk_tolerance": "Medium",
        "investment_horizon": "Medium term: 6-24 months",
        "max_single_stock_weight": 15.0,
        "max_sector_weight": 35.0,
        "warn_single_stock_weight": 10.0,
        "warn_sector_weight": 25.0,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _tech():
    return TechnicalSnapshot(
        symbol="RELIANCE",
        bar_count=120,
        insufficient_data=False,
        close=110.0,
        ema20=108.0,
        ema50=105.0,
        ema200=100.0,
        rsi14=55.0,
        macd_histogram=1.0,
        macd_direction="BULLISH",
        atr14=2.0,
        atr_pct=1.8,
        support_levels=[105.0],
        resistance_levels=[115.0],
        high_52w=130.0,
        low_52w=80.0,
        distance_to_52w_high_pct=-15.4,
        distance_to_52w_low_pct=37.5,
        volume_trend=1.2,
        long_term_trend="BULL",
        medium_term_trend="BULL",
        short_term_trend="BULL",
        momentum="NEUTRAL",
        volatility="MODERATE",
        overall_trend_score=75,
        computed_at=datetime.now(timezone.utc),
    )


def _fund(**overrides):
    data = {
        "symbol": "RELIANCE",
        "company_name": "Reliance Industries",
        "sector": "Energy",
        "market_cap": 100000000000.0,
        "pe_trailing": 25.0,
        "pb": 3.0,
        "roe": 0.15,
        "net_profit_margin": 0.1,
        "revenue_growth": 0.12,
        "debt_to_equity": 0.8,
        "free_cashflow": 1000000000.0,
        "observed_at": datetime.now(timezone.utc),
    }
    data.update(overrides)
    return FundamentalsSnapshot(**data)


def test_freshness_states():
    now = datetime.now(timezone.utc)
    assert freshness_label(now) == "FRESH"
    assert freshness_label(now - timedelta(hours=2)) == "RECENT"
    assert freshness_label(now - timedelta(days=2)) == "STALE"
    assert freshness_label(None) == "unknown"


def test_position_evidence_math():
    holding = _holding(quantity=10, avg_buy_price=100.0, current_ltp=110.0)
    info = build_position_evidence(
        EvidenceBuilder(), holding, portfolio_total_value=2200.0, holding_count=2
    )
    assert info["invested"] == 1000.0
    assert info["current_value"] == 1100.0
    assert info["pnl"] == 100.0
    assert info["pnl_pct"] == 10.0
    assert info["portfolio_weight_pct"] == 50.0
    assert info["distance"]["distance_to_target_pct"] == round(
        (130.0 - 110.0) / 110.0 * 100.0, 2
    )


def test_evidence_pack_contains_all_sections():
    holding = _holding()
    holdings = [holding]
    pack, builder, quality = build_evidence_pack(
        holding, holdings, _tech(), _fund(), _profile()
    )
    assert pack["security"]["symbol"] == "RELIANCE"
    assert pack["position"]["symbol"] == "RELIANCE"
    assert pack["fundamentals"] is not None
    assert pack["technical"] is not None
    assert pack["portfolio_context"]["holding_count"] == 1
    assert pack["investment_profile"]["max_single_stock_weight_pct"] == 15.0
    assert len(builder.items) > 10
    assert pack["data_quality"]["grade"] in ("EXCELLENT", "GOOD", "MODERATE", "POOR")


def test_single_holding_always_concentration_flagged():
    holding = _holding()
    _, _, quality = build_evidence_pack(
        holding, [holding], _tech(), _fund(), _profile()
    )
    assert "PORTFOLIO_CONCENTRATION" in quality.gates


def test_missing_fundamentals_triggers_low_confidence():
    holding = _holding()
    _, _, quality = build_evidence_pack(
        holding, [holding], _tech(), None, _profile()
    )
    assert "LOW_CONFIDENCE" in quality.gates
    assert quality.score < 60


def test_stale_ltp_triggers_stale_data():
    holding = _holding(last_updated=datetime.now(timezone.utc) - timedelta(days=3))
    _, _, quality = build_evidence_pack(
        holding, [holding], _tech(), _fund(), _profile()
    )
    assert "STALE_DATA" in quality.gates


def test_insufficient_technical_data_lowers_quality():
    holding = _holding()
    tech = TechnicalSnapshot(symbol="RELIANCE", bar_count=30, insufficient_data=True)
    _, _, quality = build_evidence_pack(
        holding, [holding], tech, _fund(), _profile()
    )
    assert quality.score < 60
