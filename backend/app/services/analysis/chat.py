from __future__ import annotations

import json
from pathlib import Path

from ... import models

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

MAX_HISTORY = 10
MAX_MESSAGE_CHARS = 2000
MAX_CONTEXT_CHARS = 14000
MAX_EVIDENCE_ITEMS = 20

_system_cache: dict[str, str] | None = None


def load_chat_prompt() -> str:
    global _system_cache
    if _system_cache is None:
        _system_cache = (PROMPTS_DIR / "chat_advisor_v1.md").read_text(
            encoding="utf-8"
        )
    return _system_cache


def _rounded(value, ndigits: int = 2):
    if value is None:
        return None
    try:
        return round(float(value), ndigits)
    except (TypeError, ValueError):
        return value


def _position_snapshot(holding: models.Holding) -> dict:
    qty = float(holding.quantity)
    avg = float(holding.avg_buy_price)
    invested = qty * avg
    ltp = float(holding.current_ltp) if holding.current_ltp is not None else None
    current_value = qty * ltp if ltp is not None else None
    pnl = current_value - invested if current_value is not None else None
    pnl_pct = pnl / invested * 100.0 if pnl is not None and invested else None
    return {
        "symbol": holding.symbol,
        "quantity": _rounded(qty, 3),
        "avg_buy_price": _rounded(avg),
        "invested": _rounded(invested),
        "current_ltp": _rounded(ltp),
        "current_value": _rounded(current_value),
        "pnl": _rounded(pnl),
        "pnl_pct": _rounded(pnl_pct),
        "stop_loss": _rounded(holding.stop_loss),
        "target_price": _rounded(holding.target_price),
        "broker": holding.broker,
        "sector": holding.sector,
        "ltp_last_updated": (
            holding.last_updated.isoformat() if holding.last_updated else None
        ),
    }


def _profile_dict(profile: models.InvestmentProfile) -> dict:
    return {
        "investment_style": profile.investment_style,
        "risk_tolerance": profile.risk_tolerance,
        "investment_horizon": profile.investment_horizon,
        "max_single_stock_weight_pct": float(profile.max_single_stock_weight),
        "max_sector_weight_pct": float(profile.max_sector_weight),
    }


def _recommendation_dict(
    rec: models.Recommendation,
    position: dict | None = None,
    include_evidence: bool = True,
) -> dict:
    evidence = rec.evidence
    if not isinstance(evidence, list):
        evidence = None
    if include_evidence and evidence:
        evidence = [
            item for item in evidence[:MAX_EVIDENCE_ITEMS] if isinstance(item, dict)
        ]
    else:
        evidence = None
    return {
        "kind": rec.kind,
        "symbol": rec.symbol,
        "rating": rec.rating,
        "action": rec.action,
        "confidence": rec.confidence,
        "scores": rec.scores,
        "portfolio_weight_pct": _rounded(rec.portfolio_weight),
        "thesis_status": rec.thesis_status,
        "summary": rec.summary,
        "why": rec.why,
        "bull_case": rec.bull_case,
        "base_case": rec.base_case,
        "bear_case": rec.bear_case,
        "key_reasons": rec.key_reasons,
        "key_risks": rec.key_risks,
        "buy_conditions": rec.buy_conditions,
        "reduce_conditions": rec.reduce_conditions,
        "exit_conditions": rec.exit_conditions,
        "support_levels": rec.support_levels,
        "resistance_levels": rec.resistance_levels,
        "fair_value_range": rec.fair_value_range,
        "data_quality": rec.data_quality,
        "quality_flags": rec.quality_flags,
        "health_score": rec.health_score,
        "positives": rec.positives,
        "concerns": rec.concerns,
        "priority_note": rec.priority_note,
        "analysis_timestamps": rec.analysis_timestamps,
        "position": position,
        "evidence": evidence,
    }


def build_holding_chat_context(
    holding: models.Holding,
    rec: models.Recommendation,
    holdings: list[models.Holding],
    profile: models.InvestmentProfile,
) -> dict:
    return {
        "mode": "holding",
        "security": {
            "symbol": holding.symbol,
            "sector": holding.sector,
            "broker": holding.broker,
        },
        "recommendation": _recommendation_dict(
            rec, position=_position_snapshot(holding)
        ),
        "portfolio_context": {
            "holding_count": len(holdings),
            "other_holdings": [
                _position_snapshot(h)
                for h in holdings
                if h.id != holding.id
            ][:10],
        },
        "investment_profile": _profile_dict(profile),
    }


def build_portfolio_chat_context(
    portfolio_rec: models.Recommendation | None,
    holding_recs: list[models.Recommendation],
    holdings: list[models.Holding],
    profile: models.InvestmentProfile,
) -> dict:
    rows = []
    for rec in holding_recs:
        matching = next((h for h in holdings if h.symbol == rec.symbol), None)
        rows.append(
            {
                "symbol": rec.symbol,
                "rating": rec.rating,
                "action": rec.action,
                "confidence": rec.confidence,
                "summary": rec.summary,
                "portfolio_weight_pct": _rounded(rec.portfolio_weight),
                "position": _position_snapshot(matching) if matching else None,
            }
        )
    return {
        "mode": "portfolio",
        "portfolio_recommendation": (
            _recommendation_dict(portfolio_rec, include_evidence=False)
            if portfolio_rec is not None
            else None
        ),
        "holdings": rows[:25],
        "investment_profile": _profile_dict(profile),
    }


def render_chat_prompt(
    context: dict,
    history: list[dict],
    question: str,
) -> str:
    payload = {
        "context": context,
        "history": history[-MAX_HISTORY:],
        "user_question": question,
    }
    serialized = json.dumps(payload, indent=2, default=str)
    if len(serialized) > MAX_CONTEXT_CHARS:
        serialized = serialized[:MAX_CONTEXT_CHARS] + "\n... (truncated)"
    return load_chat_prompt() + "\n\nCONTEXT:\n" + serialized
