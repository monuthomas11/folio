from datetime import date

from .conftest import auth_headers


def _register(client, email="tradebook@test.com"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Trader"},
    ).json()["access_token"]


def _create(client, token, **overrides):
    payload = {
        "symbol": "RELIANCE",
        "side": "long",
        "entryDate": "2026-01-10",
        "entryQuantity": 10,
        "entryPrice": 100,
        "broker": "Zerodha",
        "notes": None,
    }
    payload.update(overrides)
    response = client.post("/tradebook", json=payload, headers=auth_headers(token))
    assert response.status_code == 201, response.text
    return response.json()


def test_long_trade_partial_exit_and_totals(client):
    token = _register(client)
    headers = auth_headers(token)
    trade = _create(client, token)

    exit_response = client.post(
        f"/tradebook/{trade['id']}/exits",
        json={
            "quantity": 4,
            "exitPrice": 120,
            "exitDate": "2026-01-20",
            "notes": "Took partial profits at resistance",
        },
        headers=headers,
    )
    assert exit_response.status_code == 201, exit_response.text
    row = exit_response.json()
    assert row["remainingQuantity"] == 6.0
    assert row["realizedPnl"] == 80.0
    assert row["unrealizedPnl"] is None
    assert row["notes"] == "Took partial profits at resistance"

    listing = client.get("/tradebook", headers=headers)
    assert listing.status_code == 200
    data = listing.json()
    assert data["summary"]["realizedPnl"] == 80.0
    assert data["summary"]["unpricedOpenCount"] == 1
    assert data["summary"]["totalPnl"] is None


def test_short_trade_price_refresh_and_close(client, monkeypatch):
    token = _register(client, "short-tradebook@test.com")
    headers = auth_headers(token)
    trade = _create(
        client,
        token,
        symbol="TCS",
        side="short",
        entryDate="2026-02-01",
        entryQuantity=5,
        entryPrice=200,
    )

    import app.routers.tradebook as tradebook_router

    monkeypatch.setattr(
        tradebook_router,
        "fetch_price_data",
        lambda symbols: ({"TCS": 170.0}, {"TCS": -1.0}, {}),
    )
    refreshed = client.post("/tradebook/fetch-all", headers=headers)
    assert refreshed.status_code == 200
    row = refreshed.json()["trades"][0]
    assert row["unrealizedPnl"] == 150.0
    assert row["totalPnl"] == 150.0

    closed = client.post(
        f"/tradebook/{trade['id']}/exits",
        json={"quantity": 5, "exitPrice": 160, "exitDate": "2026-02-03"},
        headers=headers,
    )
    assert closed.status_code == 201
    assert closed.json()["status"] == "closed"
    assert closed.json()["realizedPnl"] == 200.0

    locked = client.put(
        f"/tradebook/{trade['id']}",
        json={
            "symbol": "TCS",
            "side": "short",
            "entryDate": "2026-02-01",
            "entryQuantity": 5,
            "entryPrice": 190,
            "broker": "Zerodha",
            "notes": None,
        },
        headers=headers,
    )
    assert locked.status_code == 409


def test_tradebook_is_user_scoped_and_validates_exit_date(client):
    owner = _register(client, "tradebook-owner@test.com")
    other = _register(client, "tradebook-other@test.com")
    trade = _create(client, owner)

    forbidden = client.get("/tradebook", headers=auth_headers(other))
    assert forbidden.status_code == 200
    assert forbidden.json()["trades"] == []

    invalid = client.post(
        f"/tradebook/{trade['id']}/exits",
        json={"quantity": 1, "exitPrice": 90, "exitDate": "2026-01-01"},
        headers=auth_headers(owner),
    )
    assert invalid.status_code == 422

    missing = client.post(
        f"/tradebook/{trade['id']}/exits",
        json={"quantity": 1, "exitPrice": 90, "exitDate": date.today().isoformat()},
        headers=auth_headers(other),
    )
    assert missing.status_code == 404
