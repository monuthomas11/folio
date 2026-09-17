import app.routers.holdings as holdings_router

from .conftest import auth_headers


def _register(client, email="al@test.com"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Alerts"},
    ).json()["access_token"]


def _patch_prices(monkeypatch, price_map):
    def fake_ltps(symbols):
        prices = {}
        errors = {}
        for symbol in symbols:
            if symbol in price_map:
                prices[symbol] = price_map[symbol]
            else:
                errors[symbol] = "no data"
        return prices, errors

    monkeypatch.setattr(
        holdings_router,
        "fetch_price_data",
        lambda symbols: (
            fake_ltps(symbols)[0],
            {symbol: None for symbol in symbols},
            fake_ltps(symbols)[1],
        ),
    )
    monkeypatch.setattr(holdings_router, "fetch_sector", lambda symbol: None)


def _create_holding(client, token, symbol="TATAMOTORS", **overrides):
    payload = {
        "symbol": symbol,
        "quantity": 10,
        "avgBuyPrice": 100.0,
        "stopLoss": None,
        "targetPrice": None,
        "broker": "Groww",
    }
    payload.update(overrides)
    return client.post(
        "/holdings", json=payload, headers=auth_headers(token)
    ).json()["id"]


def test_no_alerts_when_none_set(client, monkeypatch):
    _patch_prices(monkeypatch, {"TATAMOTORS": 105.0})
    token = _register(client)
    _create_holding(client, token)
    client.post("/holdings/fetch-all", headers=auth_headers(token))
    r = client.get("/alerts", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json() == []


def test_sl_and_target_alerts_on_fetch(client, monkeypatch):
    _patch_prices(monkeypatch, {"TATAMOTORS": 45.0, "INFY": 250.0})
    token = _register(client, "b@test.com")

    sl_id = _create_holding(
        client, token, symbol="TATAMOTORS", stopLoss=50.0, avgBuyPrice=100.0
    )
    tgt_id = _create_holding(
        client, token, symbol="INFY", targetPrice=200.0, avgBuyPrice=100.0
    )
    holding_ids = {sl_id, tgt_id}

    r = client.post("/holdings/fetch-all", headers=auth_headers(token))
    assert r.status_code == 200

    alerts = client.get("/alerts", headers=auth_headers(token)).json()
    assert len(alerts) == 2
    kinds = {a["kind"] for a in alerts}
    assert kinds == {"sl-hit", "target-hit"}
    assert all(not a["dismissed"] for a in alerts)
    assert all(a["holdingId"] in holding_ids for a in alerts)

    first = alerts[0]
    r = client.put(f"/alerts/{first['id']}/dismiss", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["dismissed"] is True

    remaining = client.get("/alerts", headers=auth_headers(token)).json()
    assert len(remaining) == 1
    assert remaining[0]["id"] != first["id"]

    all_alerts = client.get(
        "/alerts?include_dismissed=true", headers=auth_headers(token)
    ).json()
    assert len(all_alerts) == 2


def test_no_duplicate_alert_on_refetch(client, monkeypatch):
    _patch_prices(monkeypatch, {"TATAMOTORS": 45.0})
    token = _register(client, "e@test.com")
    _create_holding(client, token, stopLoss=50.0)

    for _ in range(3):
        client.post("/holdings/fetch-all", headers=auth_headers(token))

    alerts = client.get("/alerts", headers=auth_headers(token)).json()
    assert len(alerts) == 1


def test_no_alerts_when_price_between_sl_and_target(client, monkeypatch):
    _patch_prices(monkeypatch, {"TATAMOTORS": 105.0})
    token = _register(client, "f@test.com")
    _create_holding(client, token, stopLoss=50.0, targetPrice=200.0)

    client.post("/holdings/fetch-all", headers=auth_headers(token))

    alerts = client.get("/alerts", headers=auth_headers(token)).json()
    assert alerts == []


def test_alert_recreated_after_dismiss_when_still_crossed(client, monkeypatch):
    _patch_prices(monkeypatch, {"TATAMOTORS": 45.0})
    token = _register(client, "g@test.com")
    _create_holding(client, token, stopLoss=50.0)

    client.post("/holdings/fetch-all", headers=auth_headers(token))
    alert = client.get("/alerts", headers=auth_headers(token)).json()[0]
    client.put(f"/alerts/{alert['id']}/dismiss", headers=auth_headers(token))

    client.post("/holdings/fetch-all", headers=auth_headers(token))
    alerts = client.get("/alerts", headers=auth_headers(token)).json()
    assert len(alerts) == 1


def test_cannot_dismiss_other_users_alert(client, monkeypatch):
    _patch_prices(monkeypatch, {"TATAMOTORS": 45.0})
    token_a = _register(client, "c@test.com")
    _create_holding(client, token_a, stopLoss=50.0)
    client.post("/holdings/fetch-all", headers=auth_headers(token_a))
    alert = client.get("/alerts", headers=auth_headers(token_a)).json()[0]

    token_b = _register(client, "d@test.com")
    r = client.put(
        f"/alerts/{alert['id']}/dismiss", headers=auth_headers(token_b)
    )
    assert r.status_code == 404
