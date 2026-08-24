import asyncio

from app.services.analysis.prompts import render_agent_prompt
from app.services.llm.mock_provider import MockProvider
EVIDENCE_PACK = {
    "security": {"symbol": "TEST", "sector": "IT", "broker": None},
    "position": {
        "symbol": "TEST",
        "quantity": 10,
        "avg_buy_price": 100.0,
        "invested": 1000.0,
        "current_ltp": 110.0,
        "current_value": 1100.0,
        "pnl": 100.0,
        "pnl_pct": 10.0,
        "portfolio_weight_pct": 5.0,
        "stop_loss": 90.0,
        "target_price": 130.0,
        "broker": None,
        "sector": "IT",
        "distance": {},
    },
    "fundamentals": {
        "company_name": "Test Corp",
        "sector": "IT",
        "market_cap": 1e9,
        "pe_trailing": 20.0,
        "roe": 0.15,
    },
    "technical": {"overall_trend_score": 70, "rsi14": 55.0},
    "portfolio_context": {
        "total_value": 1100.0,
        "holding_count": 1,
        "sector_weights": [{"sector": "IT", "weight_pct": 100.0}],
        "concentration_warnings": [],
    },
    "investment_profile": {"max_single_stock_weight_pct": 15.0},
    "evidence": [
        {
            "id": "E001",
            "category": "position",
            "label": "Quantity",
            "value": 10,
            "unit": "shares",
            "source": "user-input",
            "freshness": "FRESH",
            "confidence": "HIGH",
        }
    ],
    "data_quality": {"score": 75, "grade": "GOOD", "gates": []},
}


def _run(agent, extra=None):
    provider = MockProvider()
    prompt = render_agent_prompt(agent, EVIDENCE_PACK, extra)
    return asyncio.run(provider.generate_json("system", prompt))


def test_mock_fundamental_schema():
    out = _run("fundamental")
    assert "fundamental_score" in out
    assert "business_quality_score" in out
    assert "valuation_regime" in out
    assert isinstance(out["strengths"], list)


def test_mock_technical_schema():
    out = _run("technical")
    assert "technical_score" in out
    assert out["entry_quality"] in ("GOOD_ENTRY", "WAIT", "POOR_ENTRY")
    assert isinstance(out["support_levels"], list)


def test_mock_portfolio_schema():
    out = _run("portfolio")
    assert "portfolio_fit_score" in out
    assert "concentration_flags" in out
    assert isinstance(out["concentration_flags"], list)


def test_mock_committee_holding_schema():
    out = _run(
        "committee",
        extra={"mode": "holding", "agent_outputs": {}},
    )
    assert out["rating"] in ("BUY", "HOLD", "REDUCE", "EXIT")
    assert 0 <= out["confidence"] <= 100
    assert "summary" in out
    assert "bull_case" in out
    assert "bear_case" in out
    assert "fair_value_range" in out
    assert isinstance(out["evidence_ids"], list)


def test_mock_committee_portfolio_schema():
    out = _run("committee", extra={"mode": "portfolio"})
    assert "health_score" in out
    assert "positives" in out
    assert "concerns" in out
    assert "priority" in out
    assert "stock_actions" in out


def test_mock_chat_returns_plain_text():
    provider = MockProvider()
    prompt = (
        "system\n<<AGENT:chat>>\n"
        'CONTEXT: {"symbol": "HDFCBANK", "rating": "HOLD", '
        '"action": "HOLD_MONITOR", "user_question": "Will it recover?"}'
    )
    reply = asyncio.run(
        provider.generate_text("system", prompt, json_mode=False)
    )
    assert isinstance(reply, str)
    assert not reply.lstrip().startswith("{")
    assert "HOLD" in reply
