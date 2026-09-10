import uuid

from .conftest import auth_headers
from app.database import SessionLocal
from app.models import Alert, AnalysisRun, Recommendation


def _register(client, email="h@test.com"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Holder"},
    ).json()["access_token"]


def _holding_payload(**overrides):
    payload = {
        "symbol": "RELIANCE",
        "quantity": 10,
        "avgBuyPrice": 2500.0,
        "stopLoss": 2200.0,
        "targetPrice": 3200.0,
        "broker": "Zerodha",
    }
    payload.update(overrides)
    return payload


def test_create_and_list(client):
    token = _register(client)
    headers = auth_headers(token)
    r = client.post("/holdings", json=_holding_payload(), headers=headers)
    assert r.status_code == 201
    body = r.json()
    assert body["symbol"] == "RELIANCE"
    assert body["quantity"] == 10
    assert body["avgBuyPrice"] == 2500.0
    assert body["currentLtp"] is None

    listing = client.get("/holdings", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_update_holding(client):
    token = _register(client)
    headers = auth_headers(token)
    hid = client.post("/holdings", json=_holding_payload(), headers=headers).json()["id"]
    r = client.put(
        f"/holdings/{hid}",
        json=_holding_payload(quantity=25, targetPrice=4000),
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["quantity"] == 25
    assert r.json()["targetPrice"] == 4000


def test_delete_holding(client):
    token = _register(client)
    headers = auth_headers(token)
    hid = client.post("/holdings", json=_holding_payload(), headers=headers).json()["id"]
    assert client.delete(f"/holdings/{hid}", headers=headers).status_code == 204
    assert client.get("/holdings", headers=headers).json() == []


def test_delete_holding_deletes_referenced_records(client):
    token = _register(client, "analysis-delete@h.com")
    headers = auth_headers(token)
    holding = client.post("/holdings", json=_holding_payload(), headers=headers).json()

    db = SessionLocal()
    try:
        run = AnalysisRun(
            user_id=uuid.UUID(client.get("/auth/me", headers=headers).json()["id"]),
            kind="holding",
            holding_id=uuid.UUID(holding["id"]),
            provider="mock",
        )
        db.add(run)
        db.flush()
        recommendation = Recommendation(
            run_id=run.id,
            user_id=run.user_id,
            holding_id=run.holding_id,
            kind="holding",
            symbol="RELIANCE",
            rating="HOLD",
            action="HOLD",
            summary="Test recommendation",
            key_reasons=[],
            key_risks=[],
            buy_conditions=[],
            reduce_conditions=[],
            exit_conditions=[],
            support_levels=[],
            resistance_levels=[],
            evidence_ids=[],
            data_quality="GOOD",
            positives=[],
            concerns=[],
        )
        db.add(recommendation)
        alert = Alert(
            user_id=run.user_id,
            holding_id=run.holding_id,
            symbol="RELIANCE",
            kind="target-hit",
            price=3200.0,
        )
        db.add(alert)
        db.commit()
        run_id = run.id
        recommendation_id = recommendation.id
        alert_id = alert.id
    finally:
        db.close()

    assert client.delete(f"/holdings/{holding['id']}", headers=headers).status_code == 204

    db = SessionLocal()
    try:
        assert db.get(AnalysisRun, run_id) is None
        assert db.get(Recommendation, recommendation_id) is None
        assert db.get(Alert, alert_id) is None
    finally:
        db.close()


def test_update_other_users_holding_not_found(client):
    token_a = _register(client, "a@h.com")
    token_b = _register(client, "b@h.com")
    hid = client.post(
        "/holdings", json=_holding_payload(), headers=auth_headers(token_a)
    ).json()["id"]
    r = client.put(
        f"/holdings/{hid}", json=_holding_payload(), headers=auth_headers(token_b)
    )
    assert r.status_code == 404


def test_delete_other_users_holding_not_found(client):
    token_a = _register(client, "c@h.com")
    token_b = _register(client, "d@h.com")
    hid = client.post(
        "/holdings", json=_holding_payload(), headers=auth_headers(token_a)
    ).json()["id"]
    assert client.delete(f"/holdings/{hid}", headers=auth_headers(token_b)).status_code == 404


def test_validation_errors(client):
    token = _register(client)
    headers = auth_headers(token)
    assert client.post("/holdings", json=_holding_payload(quantity=0), headers=headers).status_code == 422
    assert client.post("/holdings", json=_holding_payload(avgBuyPrice=-5), headers=headers).status_code == 422


def test_cannot_access_other_user_list(client):
    token_a = _register(client, "e@h.com")
    client.post("/holdings", json=_holding_payload(), headers=auth_headers(token_a))
    token_b = _register(client, "f@h.com")
    assert client.get("/holdings", headers=auth_headers(token_b)).json() == []


CSV_HEADER = "symbol,quantity,avg_buy_price,stop_loss,target_price,broker,sector"


def test_export_holdings_csv(client):
    token = _register(client)
    headers = auth_headers(token)
    client.post("/holdings", json=_holding_payload(broker="Zerodha, Inc"), headers=headers)
    r = client.get("/holdings/export", headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    lines = r.text.strip().splitlines()
    assert lines[0] == CSV_HEADER
    assert "RELIANCE,10,2500,2200,3200,\"Zerodha, Inc\"," in lines[1]


def test_export_roundtrip_import(client):
    token = _register(client)
    headers = auth_headers(token)
    client.post("/holdings", json=_holding_payload(), headers=headers)
    exported = client.get("/holdings/export", headers=headers).text

    other = client.post(
        "/auth/register",
        json={"email": "g@h.com", "password": "password123", "name": "Importer"},
    ).json()["access_token"]
    other_headers = auth_headers(other)
    r = client.post("/holdings/import", json={"csv": exported}, headers=other_headers)
    assert r.status_code == 200
    assert r.json() == {"created": 1, "errors": []}
    listing = client.get("/holdings", headers=other_headers).json()
    assert len(listing) == 1
    assert listing[0]["symbol"] == "RELIANCE"
    assert listing[0]["avgBuyPrice"] == 2500.0


def test_import_skips_empty_and_reports_bad_rows(client):
    token = _register(client)
    headers = auth_headers(token)
    csv_text = (
        f"{CSV_HEADER}\n"
        "TCS,5,3500,,,Groww,IT\n"
        ",\n"
        "BADSYM,0,100,,,,\n"
    )
    r = client.post("/holdings/import", json={"csv": csv_text}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["created"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row"] == 4
    assert "quantity" in body["errors"][0]["message"]

    listing = client.get("/holdings", headers=headers).json()
    assert [h["symbol"] for h in listing] == ["TCS"]


def test_import_requires_symbol_header(client):
    token = _register(client)
    headers = auth_headers(token)
    r = client.post("/holdings/import", json={"csv": "foo,bar\n1,2\n"}, headers=headers)
    assert r.status_code == 422


def test_import_isolated_per_user(client):
    token_a = _register(client, "h@h.com")
    token_b = _register(client, "i@h.com")
    csv_text = f"{CSV_HEADER}\nINFY,2,1500,,,,\n"
    client.post("/holdings/import", json={"csv": csv_text}, headers=auth_headers(token_a))
    assert client.get("/holdings", headers=auth_headers(token_b)).json() == []
