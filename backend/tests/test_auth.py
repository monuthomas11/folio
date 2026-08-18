from .conftest import auth_headers


def test_register(client):
    r = client.post(
        "/auth/register",
        json={"email": "a@test.com", "password": "password123", "name": "Alpha"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "a@test.com"
    assert "password" not in str(body["user"])


def test_register_duplicate_email(client):
    payload = {"email": "dup@test.com", "password": "password123", "name": "Dup"}
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409


def test_login_success(client):
    client.post(
        "/auth/register",
        json={"email": "l@test.com", "password": "password123", "name": "Login"},
    )
    r = client.post(
        "/auth/login", json={"email": "l@test.com", "password": "password123"}
    )
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        json={"email": "w@test.com", "password": "password123", "name": "Wrong"},
    )
    r = client.post("/auth/login", json={"email": "w@test.com", "password": "nope"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer bogus"}).status_code == 401


def test_me_returns_user(client):
    token = client.post(
        "/auth/register",
        json={"email": "me@test.com", "password": "password123", "name": "Me"},
    ).json()["access_token"]
    r = client.get("/auth/me", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["email"] == "me@test.com"