import app.routers.holdings as holdings_router

from .conftest import auth_headers


def _register(client, email="fp@test.com"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Fetch"},
    ).json()["access_token"]


def _create(client, token, symbol, avg_buy_price, quantity=10, **overrides):
    payload = {
        "symbol": symbol,
        "quantity": quantity,
        "avgBuyPrice": avg_buy_price,
        "stopLoss": None,
        "targetPrice": None,
        "broker": None,
    }
    payload.update(overrides)
    return client.post("/holdings", json=payload, headers=auth_headers(token)).json()


def test_fetch_price_updates_holding(client, monkeypatch):
    monkeypatch.setattr(holdings_router, "fetch_ltp", lambda symbol: 2876.5)
    monkeypatch.setattr(holdings_router, "fetch_sector", lambda symbol: "Energy")
    token = _register(client)
    headers = auth_headers(token)
    holding = _create(client, token, "RELIANCE", 2500.0)

    r = client.post("/holdings/fetch-price/RELIANCE", headers=headers)
    assert r.status_code == 200
    assert r.json()["ltp"] == 2876.5

    updated = next(
        h for h in client.get("/holdings", headers=headers).json()
        if h["id"] == holding["id"]
    )
    assert updated["currentLtp"] == 2876.5
    assert updated["lastUpdated"] is not None
    assert updated["sector"] == "Energy"


def test_fetch_price_symbol_not_owned(client, monkeypatch):
    token = _register(client, "f2@test.com")
    r = client.post(
        "/holdings/fetch-price/RELIANCE", headers=auth_headers(token)
    )
    assert r.status_code == 404


def test_fetch_price_yfinance_error(client, monkeypatch):
    def boom(symbol):
        raise ValueError("network down")

    monkeypatch.setattr(holdings_router, "fetch_ltp", boom)
    token = _register(client, "f3@test.com")
    _create(client, token, "TCS", 3000.0)
    r = client.post("/holdings/fetch-price/TCS", headers=auth_headers(token))
    assert r.status_code == 502


def test_fetch_all_updates_all(client, monkeypatch):
    monkeypatch.setattr(
        holdings_router,
        "fetch_ltps",
        lambda symbols: ({"RELIANCE": 100.0, "TCS": 200.0}, {}),
    )
    monkeypatch.setattr(holdings_router, "fetch_sector", lambda symbol: "Tech")
    token = _register(client, "f4@test.com")
    headers = auth_headers(token)
    _create(client, token, "RELIANCE", 80.0)
    _create(client, token, "TCS", 150.0)

    r = client.post("/holdings/fetch-all", headers=headers)
    assert r.status_code == 200
    by_symbol = {h["symbol"]: h for h in r.json()}
    assert by_symbol["RELIANCE"]["currentLtp"] == 100.0
    assert by_symbol["TCS"]["currentLtp"] == 200.0
    assert by_symbol["RELIANCE"]["sector"] == "Tech"
    assert by_symbol["TCS"]["sector"] == "Tech"


def test_dashboard_snapshot(client, monkeypatch):
    def fake_ltps(symbols):
        prices = {"RELIANCE": 120.0, "TITAN": 120.0}
        return prices, {}

    monkeypatch.setattr(holdings_router, "fetch_ltps", fake_ltps)
    monkeypatch.setattr(holdings_router, "fetch_sector", lambda symbol: "Auto")
    token = _register(client, "f5@test.com")
    headers = auth_headers(token)
    _create(client, token, "RELIANCE", 100.0, quantity=10)
    _create(client, token, "TITAN", 140.0, quantity=10, stopLoss=130.0)

    client.post("/holdings/fetch-all", headers=headers)

    r = client.get("/dashboard", headers=headers)
    assert r.status_code == 200
    body = r.json()

    assert body["summary"]["holdingCount"] == 2
    assert body["summary"]["invested"] == 2400.0
    assert body["summary"]["portfolioValue"] == 2400.0
    assert body["summary"]["totalPnl"] == 0.0
    assert body["summary"]["gainers"] == 1
    assert body["summary"]["losers"] == 1
    assert body["summary"]["activeAlertCount"] == 1
    assert len(body["holdings"]) == 2
    assert len(body["alerts"]) == 1
    assert body["alerts"][0]["kind"] == "sl-hit"