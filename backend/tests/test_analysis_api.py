import time
from datetime import date, timedelta

import pytest

from .conftest import auth_headers

from app.services.analysis import orchestrator
from app.services.fundamentals.base import FundamentalsSnapshot
from app.services.market_data.base import OHLCV


class FakeMarketData:
    def get_ltp(self, symbol: str) -> float:
        return 110.0

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
    yield


def _register(client, email="a@test.com"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Analyst"},
    ).json()["access_token"]


def _holding_payload(**overrides):
    payload = {
        "symbol": "RELIANCE",
        "quantity": 10,
        "avgBuyPrice": 100.0,
        "stopLoss": 90.0,
        "targetPrice": 130.0,
        "broker": "Zerodha",
    }
    payload.update(overrides)
    return payload


def _add_holding(client, headers, **overrides):
    r = client.post("/holdings", json=_holding_payload(**overrides), headers=headers)
    assert r.status_code == 201
    return r.json()


def _poll_run(client, headers, run_id, tries=40):
    body = None
    for _ in range(tries):
        r = client.get(f"/analysis/{run_id}", headers=headers)
        assert r.status_code == 200
        body = r.json()
        if body["status"] in ("COMPLETED", "PARTIAL_COMPLETION", "FAILED"):
            return body
        time.sleep(0.05)
    raise AssertionError(f"run did not reach terminal state: {body}")


def test_holding_analysis_flow(client):
    token = _register(client)
    headers = auth_headers(token)
    holding = _add_holding(client, headers)

    r = client.post(f"/analysis/holding/{holding['id']}", headers=headers)
    assert r.status_code == 202
    run_id = r.json()["runId"]

    run = _poll_run(client, headers, run_id)
    assert run["status"] == "COMPLETED"
    assert run["kind"] == "holding"
    assert run["provider"] == "mock"
    assert run["recommendationIds"], "expected at least one recommendation"

    rec = client.get(
        f"/analysis/latest/holding/{holding['id']}", headers=headers
    ).json()
    assert rec["rating"] in ("BUY", "HOLD", "REDUCE", "EXIT")
    assert rec["symbol"] == "RELIANCE"
    assert rec["bullCase"] and rec["bearCase"]
    assert rec["evidenceIds"]
    assert rec["dataQuality"] in ("EXCELLENT", "GOOD", "MODERATE", "POOR")


def test_latest_holding_analysis_404_before_any_run(client):
    token = _register(client)
    headers = auth_headers(token)
    holding = _add_holding(client, headers)
    r = client.get(f"/analysis/latest/holding/{holding['id']}", headers=headers)
    assert r.status_code == 404


def test_portfolio_analysis_flow(client):
    token = _register(client)
    headers = auth_headers(token)
    _add_holding(client, headers, symbol="RELIANCE")
    _add_holding(client, headers, symbol="TCS")

    r = client.post("/analysis/portfolio", headers=headers)
    assert r.status_code == 202
    run_id = r.json()["runId"]

    run = _poll_run(client, headers, run_id)
    assert run["status"] in ("COMPLETED", "PARTIAL_COMPLETION")
    assert len(run["recommendationIds"]) == 3

    latest = client.get("/analysis/latest/portfolio", headers=headers).json()
    assert latest["portfolio"] is not None
    assert latest["portfolio"]["kind"] == "portfolio"
    assert len(latest["holdings"]) == 2
    symbols = {h["symbol"] for h in latest["holdings"]}
    assert symbols == {"RELIANCE", "TCS"}


def test_second_immediate_run_rejected(client):
    token = _register(client)
    headers = auth_headers(token)
    holding = _add_holding(client, headers)

    r1 = client.post(f"/analysis/holding/{holding['id']}", headers=headers)
    assert r1.status_code == 202
    _poll_run(client, headers, r1.json()["runId"])

    r2 = client.post(f"/analysis/holding/{holding['id']}", headers=headers)
    assert r2.status_code == 409


def test_other_user_cannot_read_run(client):
    token_a = _register(client, "a@test.com")
    token_b = _register(client, "b@test.com")
    holding = _add_holding(client, auth_headers(token_a))

    r = client.post(
        f"/analysis/holding/{holding['id']}", headers=auth_headers(token_a)
    )
    run_id = r.json()["runId"]
    _poll_run(client, auth_headers(token_a), run_id)

    assert client.get(f"/analysis/{run_id}", headers=auth_headers(token_b)).status_code == 404


def test_other_user_cannot_analyze_my_holding(client):
    token_a = _register(client, "c@test.com")
    token_b = _register(client, "d@test.com")
    holding = _add_holding(client, auth_headers(token_a))
    r = client.post(
        f"/analysis/holding/{holding['id']}", headers=auth_headers(token_b)
    )
    assert r.status_code == 404


def test_profile_defaults_and_update(client):
    token = _register(client)
    headers = auth_headers(token)

    profile = client.get("/profile", headers=headers).json()
    assert profile["riskTolerance"] == "Medium"
    assert profile["maxSingleStockWeight"] == 15.0

    r = client.put(
        "/profile",
        json={"riskTolerance": "High", "maxSingleStockWeight": 20.0},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["riskTolerance"] == "High"
    assert body["maxSingleStockWeight"] == 20.0
    assert body["investmentStyle"] == "Moderate"
