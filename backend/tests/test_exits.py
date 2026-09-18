from .conftest import auth_headers


def _register(client, email="exit@test.com"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Exit"},
    ).json()["access_token"]


def _create(client, token, **overrides):
    payload = {
        "symbol": "RELIANCE",
        "quantity": 10,
        "avgBuyPrice": 100,
        "stopLoss": None,
        "targetPrice": None,
        "broker": "Zerodha",
    }
    payload.update(overrides)
    return client.post("/holdings", json=payload, headers=auth_headers(token)).json()


def test_partial_and_full_exit_track_realized_pnl(client):
    token = _register(client)
    headers = auth_headers(token)
    holding = _create(client, token)

    partial = client.post(
        f"/holdings/{holding['id']}/exit",
        json={"quantity": 4, "exitPrice": 120},
        headers=headers,
    )
    assert partial.status_code == 201
    assert partial.json()["realizedPnl"] == 80.0

    remaining = client.get("/holdings", headers=headers).json()
    assert remaining[0]["quantity"] == 6.0

    complete = client.post(
        f"/holdings/{holding['id']}/exit",
        json={"quantity": 6, "exitPrice": 90},
        headers=headers,
    )
    assert complete.status_code == 201
    assert complete.json()["realizedPnl"] == -60.0
    assert client.get("/holdings", headers=headers).json() == []

    snapshot = client.get("/dashboard", headers=headers).json()
    assert snapshot["summary"]["realizedPnl"] == 20.0
    assert snapshot["summary"]["realizedCostBasis"] == 1000.0
    assert snapshot["summary"]["realizedProceeds"] == 1020.0
    assert snapshot["summary"]["realizedPnlPct"] == 2.0
    assert snapshot["summary"]["closedTradeCount"] == 2
    assert len(snapshot["realizedExits"]) == 2


def test_exit_cannot_exceed_owned_quantity_or_cross_users(client):
    token = _register(client, "exit-owner@test.com")
    other_token = _register(client, "exit-other@test.com")
    holding = _create(client, token)

    too_many = client.post(
        f"/holdings/{holding['id']}/exit",
        json={"quantity": 11, "exitPrice": 100},
        headers=auth_headers(token),
    )
    assert too_many.status_code == 422

    forbidden = client.post(
        f"/holdings/{holding['id']}/exit",
        json={"quantity": 1, "exitPrice": 100},
        headers=auth_headers(other_token),
    )
    assert forbidden.status_code == 404
