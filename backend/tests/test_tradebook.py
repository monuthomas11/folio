from datetime import date

import pytest

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


def test_fno_option_lots_charges_marks_and_partial_exit(client):
    token = _register(client, "fno-tradebook@test.com")
    headers = auth_headers(token)
    zero_charges = {
        "brokerage": 1,
        "sttCtt": 2,
        "exchangeTransaction": 3,
        "sebi": 1,
        "gst": 1,
        "stampDuty": 0,
        "ipft": 0,
        "other": 0,
        "contractNoteRef": "CN-1",
    }
    created = client.post(
        "/tradebook",
        json={
            "symbol": "NIFTY",
            "side": "long",
            "assetClass": "fno",
            "instrumentType": "option",
            "exchange": "NSE",
            "underlyingType": "index",
            "underlyingSymbol": "NIFTY",
            "contractSymbol": "NIFTY26SEP25000CE",
            "expiryDate": "2026-09-24",
            "strikePrice": 25000,
            "tickSize": 0.05,
            "optionType": "CE",
            "lotSize": 75,
            "entryLots": 2,
            "entryDate": "2026-09-10",
            "entryPrice": 100,
            "broker": "Zerodha",
            "entryCharges": zero_charges,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    trade = created.json()
    assert trade["entryQuantity"] == 150.0
    assert trade["grossEntryValue"] == 15000.0
    assert trade["tickSize"] == 0.05
    assert trade["chargesComplete"] is True

    exited = client.post(
        f"/tradebook/{trade['id']}/exits",
        json={
            "exitLots": 1,
            "exitPrice": 120,
            "exitDate": "2026-09-12",
            "exitReason": "target",
            "charges": {**zero_charges, "contractNoteRef": "CN-2"},
        },
        headers=headers,
    )
    assert exited.status_code == 201, exited.text
    row = exited.json()
    assert row["remainingLots"] == 1
    assert row["grossRealizedPnl"] == 1500.0
    assert row["netRealizedPnl"] == 1488.0
    assert row["exits"][0]["netRealizedPnl"] == 1488.0

    marked = client.put(
        f"/tradebook/{trade['id']}/mark",
        json={"ltp": 80, "source": "manual"},
        headers=headers,
    )
    assert marked.status_code == 200, marked.text
    row = marked.json()
    assert row["grossUnrealizedPnl"] == -1500.0
    assert row["netUnrealizedPnl"] == -1504.0
    assert row["netTotalPnl"] == -16.0
    assert row["openExposure"] == 6000.0

    listing = client.get("/tradebook?assetClass=fno", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["summary"]["tradeCount"] == 1
    assert listing.json()["summary"]["openExposure"] == 6000.0


def test_fno_rejects_expiry_before_entry(client):
    token = _register(client, "fno-expiry@test.com")
    response = client.post(
        "/tradebook",
        json={
            "symbol": "NIFTY",
            "side": "long",
            "assetClass": "fno",
            "instrumentType": "future",
            "exchange": "NSE",
            "underlyingType": "index",
            "underlyingSymbol": "NIFTY",
            "contractSymbol": "NIFTY-FUT",
            "expiryDate": "2026-09-09",
            "tickSize": 0.05,
            "lotSize": 75,
            "entryLots": 1,
            "entryDate": "2026-09-10",
            "entryPrice": 25000,
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 422
    assert "Expiry date cannot be before entry date" in response.text


def test_bse_fno_quotes_require_manual_mark(monkeypatch):
    from types import SimpleNamespace

    import app.services.fno_quotes as fno_quotes

    trade = SimpleNamespace(id="bse-trade", exchange="BSE")

    class NoNetworkClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError("Unsupported exchange must not initiate quote requests")

    monkeypatch.setattr(fno_quotes.httpx, "Client", NoNetworkClient)
    prices, errors = fno_quotes.fetch_fno_prices([trade])
    assert prices == {}
    assert "manual mark" in errors[trade.id]


@pytest.mark.parametrize(
    ("instrument_type", "underlying_type", "option_type"),
    [
        ("future", "index", None),
        ("future", "stock", None),
        ("option", "index", "CE"),
        ("option", "stock", "PE"),
    ],
)
def test_fno_supported_contracts_use_lot_based_pnl_and_close(
    client, instrument_type, underlying_type, option_type
):
    token = _register(
        client,
        f"fno-{instrument_type}-{underlying_type}-{option_type or 'future'}@test.com",
    )
    headers = auth_headers(token)
    charges = {
        "brokerage": 0,
        "sttCtt": 0,
        "exchangeTransaction": 0,
        "sebi": 0,
        "gst": 0,
        "stampDuty": 0,
        "ipft": 0,
        "other": 0,
    }
    symbol = "NIFTY" if underlying_type == "index" else "RELIANCE"
    payload = {
        "symbol": symbol,
        "side": "long",
        "assetClass": "fno",
        "instrumentType": instrument_type,
        "exchange": "NSE",
        "underlyingType": underlying_type,
        "underlyingSymbol": symbol,
        "contractSymbol": f"{symbol}-2026-09-24-{instrument_type}-{option_type or 'FUT'}",
        "expiryDate": "2026-09-24",
        "tickSize": 0.05,
        "optionType": option_type,
        "strikePrice": 25000 if option_type else None,
        "lotSize": 2,
        "entryLots": 2,
        "entryDate": "2026-09-10",
        "entryPrice": 100,
        "entryCharges": charges,
    }
    created = client.post("/tradebook", json=payload, headers=headers)
    assert created.status_code == 201, created.text
    trade = created.json()
    assert trade["entryQuantity"] == 4

    closed = client.post(
        f"/tradebook/{trade['id']}/exits",
        json={
            "exitLots": 2,
            "exitPrice": 110,
            "exitDate": "2026-09-12",
            "charges": charges,
        },
        headers=headers,
    )
    assert closed.status_code == 201, closed.text
    row = closed.json()
    assert row["status"] == "closed"
    assert row["remainingLots"] == 0
    assert row["grossRealizedPnl"] == 40
    assert row["netRealizedPnl"] == 40
    assert row["exits"][0]["netRealizedPnl"] == 40


def test_fno_missing_mark_and_charges_remain_pending_until_corrected(client):
    token = _register(client, "fno-pending@test.com")
    headers = auth_headers(token)
    created = client.post(
        "/tradebook",
        json={
            "symbol": "NIFTY",
            "side": "long",
            "assetClass": "fno",
            "instrumentType": "option",
            "exchange": "NSE",
            "underlyingType": "index",
            "underlyingSymbol": "NIFTY",
            "contractSymbol": "NIFTY-2026-09-24-25000-CE",
            "expiryDate": "2026-09-24",
            "strikePrice": 25000,
            "tickSize": 0.05,
            "optionType": "CE",
            "lotSize": 2,
            "entryLots": 1,
            "entryDate": "2026-09-10",
            "entryPrice": 100,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    trade = created.json()
    assert trade["netTotalPnl"] is None
    assert trade["grossUnrealizedPnl"] is None
    assert trade["chargesComplete"] is False

    listing = client.get("/tradebook?assetClass=fno", headers=headers).json()
    assert listing["summary"]["unpricedOpenCount"] == 1
    assert listing["summary"]["incompleteChargeCount"] == 1
    assert listing["summary"]["netTotalPnl"] is None

    zero_charges = {
        "brokerage": 0,
        "sttCtt": 0,
        "exchangeTransaction": 0,
        "sebi": 0,
        "gst": 0,
        "stampDuty": 0,
        "ipft": 0,
        "other": 0,
    }
    corrected = client.put(
        f"/tradebook/{trade['id']}/charges",
        json=zero_charges,
        headers=headers,
    )
    assert corrected.status_code == 200, corrected.text
    marked = client.put(
        f"/tradebook/{trade['id']}/mark",
        json={"ltp": 80, "source": "manual"},
        headers=headers,
    )
    assert marked.status_code == 200, marked.text
    assert marked.json()["netTotalPnl"] == -40


def test_fno_rejects_short_and_invalid_contract_shape(client):
    token = _register(client, "fno-validation@test.com")
    response = client.post(
        "/tradebook",
        json={
            "symbol": "RELIANCE",
            "side": "short",
            "assetClass": "fno",
            "instrumentType": "future",
            "exchange": "NSE",
            "underlyingType": "stock",
            "underlyingSymbol": "RELIANCE",
            "contractSymbol": "RELIANCE26SEP",
            "expiryDate": "2026-09-24",
            "lotSize": 250,
            "entryLots": 1,
            "entryDate": "2026-09-10",
            "entryPrice": 100,
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 422

    invalid_option = client.post(
        "/tradebook",
        json={
            "symbol": "NIFTY",
            "side": "long",
            "assetClass": "fno",
            "instrumentType": "option",
            "exchange": "NSE",
            "underlyingType": "index",
            "underlyingSymbol": "NIFTY",
            "contractSymbol": "NIFTY26SEP25000CE",
            "expiryDate": "2026-09-24",
            "lotSize": 75,
            "entryLots": 1,
            "entryDate": "2026-09-10",
            "entryPrice": 100,
        },
        headers=auth_headers(token),
    )
    assert invalid_option.status_code == 422
