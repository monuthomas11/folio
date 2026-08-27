from __future__ import annotations

import json
import re
from typing import Any

from .base import LLMProvider

_EVIDENCE_ID_RE = re.compile(r"E\d{3}")
_SCORE_RES = {
    "fundamental_score": re.compile(r'"fundamental_score"\s*:\s*(\d+)'),
    "technical_score": re.compile(r'"technical_score"\s*:\s*(\d+)'),
    "portfolio_fit_score": re.compile(r'"portfolio_fit_score"\s*:\s*(\d+)'),
}
_TREND_SCORE_RE = re.compile(r'"overall_trend_score"\s*:\s*(\d+)')
_WEIGHT_RE = re.compile(r'"portfolio_weight_pct"\s*:\s*([0-9.]+)')


def _first_int(pattern: re.Pattern, text: str, default: int) -> int:
    match = pattern.search(text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return default
    return default


def _first_float(pattern: re.Pattern, text: str, default: float) -> float:
    match = pattern.search(text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return default
    return default


def _evidence_ids(text: str, limit: int = 8) -> list[str]:
    seen: list[str] = []
    for eid in _EVIDENCE_ID_RE.findall(text):
        if eid not in seen:
            seen.append(eid)
        if len(seen) >= limit:
            break
    return seen


def _flags_present(text: str) -> dict[str, bool]:
    return {
        "stale": "STALE_DATA" in text or '"freshness": "STALE"' in text,
        "low_confidence": "LOW_CONFIDENCE" in text,
        "concentration": "PORTFOLIO_CONCENTRATION" in text,
    }


class MockProvider(LLMProvider):
    provider_id = "mock"
    model_name = "mock-analyzer-v1"

    async def generate_text(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        json_mode: bool = True,
    ) -> str:
        full = f"{system}\n{user}"
        if "<<AGENT:fundamental>>" in full:
            payload = self._fundamental(full)
        elif "<<AGENT:technical>>" in full:
            payload = self._technical(full)
        elif "<<AGENT:portfolio>>" in full:
            payload = self._portfolio(full)
        elif "<<AGENT:committee>>" in full:
            payload = self._committee(full)
        elif "<<AGENT:chat>>" in full:
            return self._chat(full)
        else:
            payload = {"summary": "Mock provider: unknown agent marker."}
        return json.dumps(payload)

    def _fundamental(self, text: str) -> dict[str, Any]:
        flags = _flags_present(text)
        base = 55
        stale_notes: list[str] = []
        if flags["stale"]:
            stale_notes.append("Some fundamentals may be stale; verify before acting.")
        return {
            "fundamental_score": base,
            "business_quality_score": base + 5,
            "valuation_score": base - 5,
            "valuation_regime": "FAIR_VALUE",
            "earnings_quality": "UNKNOWN",
            "strengths": [
                "Profitability metrics are broadly consistent with peer averages."
            ],
            "concerns": [
                "Single data source; cross-check valuation multiples before acting."
            ],
            "stale_data_notes": stale_notes,
        }

    def _technical(self, text: str) -> dict[str, Any]:
        trend = _first_int(_TREND_SCORE_RE, text, 50)
        flags = _flags_present(text)
        if trend >= 60:
            momentum, entry = "NEUTRAL", "WAIT"
            summary = "Price is above key moving averages; trend is constructive."
            score = min(85, 45 + trend // 2)
        elif trend >= 40:
            momentum, entry = "NEUTRAL", "WAIT"
            summary = "Price is range-bound around key moving averages."
            score = 50
        else:
            momentum, entry = "NEGATIVE", "POOR_ENTRY"
            summary = "Price is below key moving averages; trend is weak."
            score = max(15, trend // 2)
        if flags["low_confidence"]:
            entry = "POOR_ENTRY"
        return {
            "technical_score": score,
            "trend_summary": summary,
            "momentum": momentum,
            "entry_quality": entry,
            "support_levels": [],
            "resistance_levels": [],
            "notes": "Computed deterministically by the mock provider.",
        }

    def _portfolio(self, text: str) -> dict[str, Any]:
        flags = _flags_present(text)
        weight = _first_float(_WEIGHT_RE, text, 0.0)
        fit = 55
        if flags["concentration"] or weight > 15:
            fit = 35
        concentration_flags: list[str] = []
        if flags["concentration"]:
            concentration_flags.append("Position exceeds max single-stock weight.")
        return {
            "portfolio_fit_score": fit,
            "oversized_positions": [],
            "concentration_flags": concentration_flags,
            "verdict": (
                "REBALANCE_BEFORE_ADDING" if flags["concentration"] else "OK_TO_MAINTAIN"
            ),
        }

    def _chat(self, text: str) -> str:
        context_section = text.split("ANALYSIS_CONTEXT:", 1)[-1]
        conversation_section = context_section
        if "LATEST_CONVERSATION:" in context_section:
            context_section, conversation_section = context_section.split(
                "LATEST_CONVERSATION:", 1
            )
        question = ""
        try:
            question = json.loads(conversation_section).get("user_question", "")
        except json.JSONDecodeError:
            if '"user_question": ' in conversation_section:
                question = conversation_section.split('"user_question": ', 1)[1].split("\n", 1)[0]
                question = question.strip().strip('\",')
        rating = "HOLD"
        action = "HOLD_MONITOR"
        symbol = None
        m = re.search(r'"rating":\s*"([^"]+)"', context_section)
        if m:
            rating = m.group(1)
        m = re.search(r'"action":\s*"([^"]+)"', context_section)
        if m:
            action = m.group(1)
        m = re.search(r'"symbol":\s*"([^"]+)"', context_section)
        if m:
            symbol = m.group(1)
        subject = symbol or "your portfolio"
        lower_question = question.lower()
        if "uptrend" in lower_question or "profit" in lower_question:
            return (
                f"It may recover, but the stored analysis does not confirm that "
                f"{subject} has returned to an uptrend. The current signal is "
                f"{rating} / {action}, so look for the stated trend-reversal trigger "
                "before assuming a profitable recovery. A loss can also deepen if "
                "the downside trigger is reached.\n\n"
                "This is informational and not personalized investment advice."
            )
        if "rating" in lower_question or "recommend" in lower_question:
            return (
                f"The latest stored view for {subject} is {rating} with action "
                f"{action}. That is the recommendation to understand first; the "
                "supporting analysis and data quality should determine whether it "
                "still fits your plan.\n\n"
                "This is informational and not personalized investment advice."
            )
        return (
            f"For {subject}, the latest stored view is {rating} with action {action}. "
            f"Your question was: \"{question}\". The answer should be guided by "
            "that recommendation, the holding data, and the available research.\n\n"
            "This is informational and not personalized investment advice."
        )

    def _committee(self, text: str) -> dict[str, Any]:
        evidence_section = text.split("EVIDENCE:")[-1]
        if '"mode": "portfolio"' in evidence_section:
            return self._committee_portfolio(text)
        return self._committee_holding(text)

    def _committee_holding(self, text: str) -> dict[str, Any]:
        scores: dict[str, Any] = {}
        for key, pattern in _SCORE_RES.items():
            value = _first_int(pattern, text, 0)
            if value > 0:
                scores[key] = value
        if scores:
            composite = int(sum(scores.values()) / len(scores))
        else:
            composite = 50
        flags = _flags_present(text)
        confidence = 70
        if flags["low_confidence"]:
            confidence -= 15
        if flags["stale"]:
            confidence -= 10

        if composite >= 65:
            rating, action, thesis = "BUY", "BUY_ON_DIPS", "STRENGTHENING"
        elif composite >= 45:
            rating, action, thesis = "HOLD", "HOLD_WAIT_FOR_TRIGGER", "VALID"
        elif composite >= 30:
            rating, action, thesis = "REDUCE", "REDUCE_ON_STRENGTH", "WEAKENING"
        else:
            rating, action, thesis = "EXIT", "EXIT_POSITION", "INVALIDATED"

        evidence = _evidence_ids(text)
        return {
            "rating": rating,
            "action": action,
            "confidence": confidence,
            "scores": {
                "business_quality": scores.get("business_quality_score"),
                "fundamental": scores.get("fundamental_score"),
                "valuation": scores.get("valuation_score"),
                "technical": scores.get("technical_score"),
                "portfolio_fit": scores.get("portfolio_fit_score"),
            },
            "thesis_status": thesis,
            "summary": (
                f"{rating}: composite score {composite} from agent evidence. "
                "Mock analysis for offline development."
            ),
            "why": "Composite of fundamental, technical and portfolio-fit agent outputs.",
            "bull_case": "Trend and fundamentals hold; price re-rates higher.",
            "base_case": "Price consolidates near current levels.",
            "bear_case": "Momentum deteriorates and broader risk-off pressurizes the position.",
            "key_reasons": ["Agent evidence supports the composite score."],
            "key_risks": [
                "Single-source data (yfinance); verify independently.",
                "Mock provider output; not real reasoning.",
            ],
            "buy_conditions": ["Fresh pullback to support with stable fundamentals."],
            "reduce_conditions": ["Weight exceeds max single-stock limit."],
            "exit_conditions": ["Thesis invalidation signals confirmed across agents."],
            "support_levels": [],
            "resistance_levels": [],
            "fair_value_range": {"low": None, "base": None, "high": None},
            "evidence_ids": evidence,
        }

    def _committee_portfolio(self, text: str) -> dict[str, Any]:
        flags = _flags_present(text)
        health = 60
        concerns: list[str] = []
        if flags["concentration"]:
            health -= 15
            concerns.append("Concentration exceeds configured limits for one or more positions.")
        if flags["stale"]:
            health -= 5
            concerns.append("Some market data was stale at analysis time; refresh before acting.")
        if flags["low_confidence"]:
            health -= 5
            concerns.append("Data gaps lower confidence in parts of this analysis.")
        return {
            "health_score": health,
            "positives": ["Positions are tracked with complete quantity and cost data."],
            "concerns": concerns,
            "priority": (
                "Review position weights against the configured limits first."
                if flags["concentration"]
                else "Maintain current allocation; review triggers before adding."
            ),
            "stock_actions": [],
            "summary": f"Portfolio health scored {health} by mock committee.",
            "evidence_ids": _evidence_ids(text),
        }
