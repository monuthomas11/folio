from app import models
from app.config import settings
from app.database import SessionLocal
from sqlalchemy import select
from app.services.api_rate_limiter import get_external_api_rate_limiter

from .conftest import auth_headers


def _register(client, email="external@test.com"):
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "External"},
    )
    return response.json()["access_token"]


def test_api_key_is_one_time_secret_and_external_endpoint_is_scoped(client):
    token = _register(client)
    response = client.post(
        "/auth/api-keys",
        json={"name": "Ideas importer"},
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    created = response.json()
    assert created["key"].startswith("folio_wk_")
    assert len(created["key"]) >= 40

    listed = client.get("/auth/api-keys", headers=auth_headers(token)).json()
    assert listed[0]["keyPrefix"] == created["keyPrefix"]
    assert "key" not in listed[0]

    item = client.post(
        "/api/v1/watchlist",
        headers={"X-Folio-API-Key": created["key"]},
        json={
            "symbol": "INFY",
            "notes": "Imported by a server-side integration",
            "levels": [{"kind": "entry", "lowerPrice": 1400, "upperPrice": 1450}],
        },
    )
    assert item.status_code == 201
    assert item.json()["symbol"] == "INFY"

    assert client.post("/api/v1/watchlist", json={"symbol": "TCS"}).status_code == 401
    assert client.post(
        "/api/v1/watchlist",
        headers={"X-Folio-API-Key": "not-a-key"},
        json={"symbol": "TCS"},
    ).status_code == 401


def test_external_endpoint_rejects_unsafe_or_unknown_input(client):
    token = _register(client, "validation@test.com")
    key = client.post(
        "/auth/api-keys", json={"name": "Validation"}, headers=auth_headers(token)
    ).json()["key"]
    headers = {"X-Folio-API-Key": key}

    assert client.post(
        "/api/v1/watchlist", headers=headers, json={"symbol": "<script>"}
    ).status_code == 422
    assert client.post(
        "/api/v1/watchlist", headers=headers, json={"symbol": "TCS", "unexpected": "x"}
    ).status_code == 422
    assert client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={"symbol": "TCS", "levels": [{"kind": "entry", "lowerPrice": "NaN"}]},
    ).status_code == 422
    assert client.post(
        "/api/v1/watchlist",
        headers=headers,
        json={"symbol": "TCS", "levels": [{"kind": "entry", "lowerPrice": 100, "upperPrice": 90}]},
    ).status_code == 422


def test_external_endpoint_rejects_oversized_body(client, monkeypatch):
    monkeypatch.setattr(settings, "external_api_max_body_bytes", 10)
    response = client.post(
        "/api/v1/watchlist",
        headers={"X-Folio-API-Key": "folio_wk_ignored"},
        json={"symbol": "TCS"},
    )
    assert response.status_code == 413


def test_revoked_api_key_and_rate_limit(client, monkeypatch):
    token = _register(client, "revoked@test.com")
    response = client.post(
        "/auth/api-keys", json={"name": "Revocable"}, headers=auth_headers(token)
    )
    key = response.json()["key"]
    key_id = response.json()["id"]
    assert client.delete(f"/auth/api-keys/{key_id}", headers=auth_headers(token)).status_code == 204
    assert client.post(
        "/api/v1/watchlist", headers={"X-Folio-API-Key": key}, json={"symbol": "TCS"}
    ).status_code == 401

    assert client.delete(
        f"/auth/api-keys/{key_id}/permanent", headers=auth_headers(token)
    ).status_code == 204
    assert client.delete(
        f"/auth/api-keys/{key_id}/permanent", headers=auth_headers(token)
    ).status_code == 404

    token = _register(client, "limited@test.com")
    key = client.post(
        "/auth/api-keys", json={"name": "Limited"}, headers=auth_headers(token)
    ).json()["key"]
    monkeypatch.setattr(settings, "external_api_rate_limit_per_minute", 1)
    limiter = get_external_api_rate_limiter()
    limiter._requests.clear()
    headers = {"X-Folio-API-Key": key}
    assert client.post("/api/v1/watchlist", headers=headers, json={"symbol": "TCS"}).status_code == 201
    limited = client.post("/api/v1/watchlist", headers=headers, json={"symbol": "INFY"})
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "60"


def test_active_api_key_must_be_revoked_before_permanent_deletion(client):
    token = _register(client, "delete-active@test.com")
    response = client.post(
        "/auth/api-keys", json={"name": "Delete guard"}, headers=auth_headers(token)
    )
    key_id = response.json()["id"]
    other_token = _register(client, "delete-other@test.com")

    assert client.delete(
        f"/auth/api-keys/{key_id}/permanent", headers=auth_headers(other_token)
    ).status_code == 404

    assert client.delete(
        f"/auth/api-keys/{key_id}/permanent", headers=auth_headers(token)
    ).status_code == 409
    assert client.delete(
        f"/auth/api-keys/{key_id}", headers=auth_headers(token)
    ).status_code == 204
    assert client.delete(
        f"/auth/api-keys/{key_id}/permanent", headers=auth_headers(token)
    ).status_code == 204
    assert all(
        item["id"] != key_id
        for item in client.get("/auth/api-keys", headers=auth_headers(token)).json()
    )


def test_api_key_is_stored_hashed(client):
    token = _register(client, "hash@test.com")
    key = client.post(
        "/auth/api-keys", json={"name": "Hash"}, headers=auth_headers(token)
    ).json()["key"]
    db = SessionLocal()
    try:
        stored = db.scalar(select(models.APIKey).where(models.APIKey.key_prefix == key[:16]))
        assert stored is not None
        assert stored.key_hash != key
        assert len(stored.key_hash) == 64
    finally:
        db.close()
