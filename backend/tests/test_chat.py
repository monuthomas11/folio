import time
from datetime import date, timedelta

import pytest

from .conftest import auth_headers

from app.services.analysis import chat, orchestrator
from app.services.fundamentals.base import FundamentalsSnapshot
from app.services.market_data.base import NewsItem, OHLCV


class FakeMarketData:
    def get_ltp(self, symbol: str) -> float:
        return 110.0

    def get_news(self, symbol: str, limit: int = 6) -> list[NewsItem]:
        return [
            NewsItem(
                title=f"{symbol} posts strong quarterly results",
                publisher="TestWire",
                summary="Revenues and margins improved sequentially.",
            )
        ]

    def get_ohlcv(self, symbol: str, period: str = "1y") -> list[OHLCV]:
        bars = []
        start = date(2024, 1, 1)
        for i in range(120):
            close = 100.0 + i * 0.5
            bars.append(
                OHLCV(
                    date=start + timedelta(days=i),
                    open=close,
                    high=close + 1.0,
                    low=close - 1.0,
                    close=close,
                    volume=1000.0,
                )
            )
        return bars


class FakeFundamentals:
    def get_snapshot(self, symbol: str) -> FundamentalsSnapshot:
        return FundamentalsSnapshot(
            symbol=symbol,
            company_name=f"{symbol} Corp",
            sector="IT",
            industry="Software",
            market_cap=1_000_000_000.0,
            currency="INR",
            pe_trailing=22.0,
            pe_forward=18.0,
            pb=3.0,
            ev_to_ebitda=15.0,
            dividend_yield=0.01,
            roe=0.18,
            net_profit_margin=0.12,
            operating_margin=0.15,
            revenue_growth=0.12,
            earnings_growth=0.1,
            debt_to_equity=0.5,
            current_ratio=2.0,
            total_cash=1e8,
            total_debt=5e7,
            free_cashflow=2e7,
            operating_cashflow=3e7,
            fifty_two_week_high=150.0,
            fifty_two_week_low=80.0,
            beta=0.9,
            source="yfinance",
        )


@pytest.fixture(autouse=True)
def _fake_providers(monkeypatch):
    monkeypatch.setattr(orchestrator, "MARKET_DATA", FakeMarketData())
    monkeypatch.setattr(orchestrator, "FUNDAMENTALS", FakeFundamentals())
    monkeypatch.setattr(chat, "MARKET_DATA", FakeMarketData())
    monkeypatch.setattr(chat, "FUNDAMENTALS", FakeFundamentals())
    yield


def _register(client, email="a@test.com"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Analyst"},
    ).json()["access_token"]


def _add_holding(client, headers, symbol="RELIANCE"):
    r = client.post(
        "/holdings",
        json={
            "symbol": symbol,
            "quantity": 10,
            "avgBuyPrice": 100.0,
            "stopLoss": 90.0,
            "targetPrice": 130.0,
            "broker": "Zerodha",
        },
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()


def _run_holding_analysis(client, headers, holding_id):
    r = client.post(f"/analysis/holding/{holding_id}", headers=headers)
    assert r.status_code == 202
    run_id = r.json()["runId"]
    for _ in range(40):
        body = client.get(f"/analysis/{run_id}", headers=headers).json()
        if body["status"] in ("COMPLETED", "PARTIAL_COMPLETION", "FAILED"):
            assert body["status"] in ("COMPLETED", "PARTIAL_COMPLETION")
            return
        time.sleep(0.05)
    raise AssertionError("run did not complete")


def _run_portfolio_analysis(client, headers):
    r = client.post("/analysis/portfolio", headers=headers)
    assert r.status_code == 202
    run_id = r.json()["runId"]
    for _ in range(40):
        body = client.get(f"/analysis/{run_id}", headers=headers).json()
        if body["status"] in ("COMPLETED", "PARTIAL_COMPLETION", "FAILED"):
            assert body["status"] in ("COMPLETED", "PARTIAL_COMPLETION")
            return
        time.sleep(0.05)
    raise AssertionError("run did not complete")


def _chat(client, headers, payload):
    return client.post("/analysis/chat", json=payload, headers=headers)


def test_chat_requires_auth(client):
    r = _chat(
        client,
        {},
        {"context": "portfolio", "message": "How am I doing?"},
    )
    assert r.status_code == 401


def test_chat_holding_no_analysis_404(client):
    token = _register(client)
    headers = auth_headers(token)
    holding = _add_holding(client, headers)
    r = _chat(
        client,
        headers,
        {"context": "holding", "holdingId": holding["id"], "message": "Hello"},
    )
    assert r.status_code == 404


def test_chat_portfolio_no_analysis_404(client):
    token = _register(client)
    headers = auth_headers(token)
    _add_holding(client, headers)
    r = _chat(client, headers, {"context": "portfolio", "message": "Hello"})
    assert r.status_code == 404


def test_chat_other_user_holding_404(client):
    token_a = _register(client, "a@test.com")
    token_b = _register(client, "b@test.com")
    holding = _add_holding(client, auth_headers(token_a))
    _run_holding_analysis(client, auth_headers(token_a), holding["id"])
    r = _chat(
        client,
        auth_headers(token_b),
        {"context": "holding", "holdingId": holding["id"], "message": "Hello"},
    )
    assert r.status_code == 404


def test_chat_empty_message_422(client):
    token = _register(client)
    headers = auth_headers(token)
    r = _chat(client, headers, {"context": "portfolio", "message": ""})
    assert r.status_code == 422


def test_chat_holding_reply_shape(client):
    token = _register(client)
    headers = auth_headers(token)
    holding = _add_holding(client, headers)
    _run_holding_analysis(client, headers, holding["id"])
    r = _chat(
        client,
        headers,
        {
            "context": "holding",
            "holdingId": holding["id"],
            "message": "Why this rating?",
            "history": [{"role": "user", "content": "Hi"}],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "reply" in body and body["reply"]
    assert body["provider"] == "mock"
    assert body["modelName"] == "mock-analyzer-v1"
    assert not body["reply"].lstrip().startswith("{")
    assert "Here is what the stored analysis says" not in body["reply"]


def test_chat_answers_question_conversationally(client):
    token = _register(client)
    headers = auth_headers(token)
    holding = _add_holding(client, headers)
    _run_holding_analysis(client, headers, holding["id"])
    r = _chat(
        client,
        headers,
        {
            "context": "holding",
            "holdingId": holding["id"],
            "message": "Would it go back to uptrend and can I make profit?",
        },
    )
    assert r.status_code == 200
    reply = r.json()["reply"]
    assert "It may recover" in reply
    assert "Current Position" not in reply


def test_render_chat_prompt_preserves_question_when_context_is_large():
    question = "Would it go back to uptrend and can I make profit?"
    prompt = chat.render_chat_prompt(
        {"large": "x" * chat.MAX_CONTEXT_CHARS}, [], question
    )
    assert question in prompt
    assert "LATEST_CONVERSATION" in prompt
    assert "Answer ONLY the user_question" in prompt


def test_chat_portfolio_reply_shape(client):
    token = _register(client)
    headers = auth_headers(token)
    _add_holding(client, headers, symbol="RELIANCE")
    _add_holding(client, headers, symbol="TCS")
    _run_portfolio_analysis(client, headers)
    r = _chat(
        client,
        headers,
        {"context": "portfolio", "message": "Which positions need attention?"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["reply"]
    assert body["provider"] == "mock"


def test_chat_holding_requires_holding_id_422(client):
    token = _register(client)
    headers = auth_headers(token)
    holding = _add_holding(client, headers)
    _run_holding_analysis(client, headers, holding["id"])
    r = _chat(
        client,
        headers,
        {"context": "holding", "message": "Hello"},
    )
    assert r.status_code == 422


def test_chat_history_capped(client):
    token = _register(client)
    headers = auth_headers(token)
    holding = _add_holding(client, headers)
    _run_holding_analysis(client, headers, holding["id"])
    history = [{"role": "user", "content": "m"}] * 25
    r = _chat(
        client,
        headers,
        {
            "context": "holding",
            "holdingId": holding["id"],
            "message": "Hello",
            "history": history,
        },
    )
    assert r.status_code == 422


def test_chat_overlong_message_422(client):
    token = _register(client)
    headers = auth_headers(token)
    r = _chat(
        client,
        headers,
        {"context": "portfolio", "message": "x" * 2001},
    )
    assert r.status_code == 422
