import app.routers.watchlist as watchlist_router

from .conftest import auth_headers


def _register(client, email="watch@test.com"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Watchlist"},
    ).json()["access_token"]


def _create(client, token, symbol="INFY", levels=None, notes=None):
    response = client.post(
        "/watchlist",
        json={"symbol": symbol, "notes": notes, "levels": levels or []},
        headers=auth_headers(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_list_update_and_validate_levels(client):
    token = _register(client)
    item = _create(
        client,
        token,
        levels=[
            {"kind": "entry", "label": "Breakout", "lowerPrice": 100, "upperPrice": 105},
            {"kind": "target", "lowerPrice": 140},
        ],
        notes="Watch earnings reaction",
    )
    assert item["symbol"] == "INFY"
    assert [level["sortOrder"] for level in item["levels"]] == [0, 1]
    assert client.get("/watchlist", headers=auth_headers(token)).json()[0]["notes"] == "Watch earnings reaction"

    updated = client.put(
        f"/watchlist/{item['id']}",
        json={
            "symbol": "INFY",
            "notes": "Updated thesis",
            "levels": [{"kind": "invalidation", "lowerPrice": 88}],
        },
        headers=auth_headers(token),
    )
    assert updated.status_code == 200
    assert updated.json()["notes"] == "Updated thesis"
    assert [level["kind"] for level in updated.json()["levels"]] == ["invalidation"]

    invalid = client.post(
        "/watchlist",
        json={"symbol": "TCS", "levels": [{"kind": "entry", "lowerPrice": 120, "upperPrice": 100}]},
        headers=auth_headers(token),
    )
    assert invalid.status_code == 422
    duplicate = client.post(
        "/watchlist",
        json={"symbol": "infy"},
        headers=auth_headers(token),
    )
    assert duplicate.status_code == 409


def test_level_semantics_transition_and_combined_alerts(client, monkeypatch):
    prices = iter([102.0, 110.0, 145.0, 120.0, 102.0])
    monkeypatch.setattr(watchlist_router, "fetch_ltp", lambda symbol: next(prices))
    token = _register(client, "semantics@test.com")
    headers = auth_headers(token)
    item = _create(
        client,
        token,
        levels=[
            {"kind": "entry", "lowerPrice": 100, "upperPrice": 105},
            {"kind": "target", "lowerPrice": 140},
            {"kind": "stop-loss", "lowerPrice": 90},
            {"kind": "invalidation", "lowerPrice": 80},
        ],
    )

    client.post("/watchlist/fetch-price/INFY", headers=headers)
    alerts = client.get("/alerts", headers=headers).json()
    assert len(alerts) == 1
    assert alerts[0]["kind"] == "entry-reached"
    assert alerts[0]["watchlistItemId"] == item["id"]
    client.put(f"/alerts/{alerts[0]['id']}/dismiss", headers=headers)

    client.post("/watchlist/fetch-price/INFY", headers=headers)
    assert client.get("/alerts", headers=headers).json() == []
    client.post("/watchlist/fetch-price/INFY", headers=headers)
    assert {a["kind"] for a in client.get("/alerts", headers=headers).json()} == {"target-reached"}
    client.post("/watchlist/fetch-price/INFY", headers=headers)
    client.post("/watchlist/fetch-price/INFY", headers=headers)
    assert {a["kind"] for a in client.get("/alerts", headers=headers).json()} == {"entry-reached", "target-reached"}


def test_watchlist_isolation_refresh_and_delete_cascade(client, monkeypatch):
    monkeypatch.setattr(watchlist_router, "fetch_ltps", lambda symbols: ({"TCS": 50.0}, {}))
    token_a = _register(client, "owner@test.com")
    token_b = _register(client, "other@test.com")
    item = _create(client, token_a, symbol="TCS", levels=[{"kind": "stop-loss", "lowerPrice": 60}])
    headers_a = auth_headers(token_a)
    headers_b = auth_headers(token_b)
    assert client.get("/watchlist", headers=headers_b).json() == []
    assert client.put(f"/watchlist/{item['id']}", json={"symbol": "TCS", "levels": []}, headers=headers_b).status_code == 404
    assert client.post("/watchlist/fetch-price/TCS", headers=headers_b).status_code == 404

    client.post("/watchlist/fetch-all", headers=headers_a)
    alert = client.get("/alerts", headers=headers_a).json()[0]
    assert client.put(f"/alerts/{alert['id']}/dismiss", headers=headers_b).status_code == 404
    assert client.delete(f"/watchlist/{item['id']}", headers=headers_a).status_code == 204
    assert client.get("/alerts?include_dismissed=true", headers=headers_a).json() == []
