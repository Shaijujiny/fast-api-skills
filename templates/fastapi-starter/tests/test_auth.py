from tests.conftest import PASSWORD, make_user


def test_login_success(client, db):
    make_user(db, "a@example.com")
    r = client.post("/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["tokenType"] == "bearer" and data["accessToken"]


def test_login_wrong_password(client, db):
    make_user(db, "a@example.com")
    r = client.post("/auth/login", json={"email": "a@example.com", "password": "wrong-password"})
    assert r.status_code == 401
    assert r.json()["code"] == "AUTH_401_INVALID_CREDENTIALS"


def test_login_inactive_user(client, db):
    make_user(db, "a@example.com", status="inactive")
    r = client.post("/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    assert r.status_code == 403


def test_error_message_is_localized(client):
    r = client.post(
        "/auth/login", json={"email": "x@example.com", "password": "whatever1"}, headers={"Accept-Language": "ar"}
    )
    assert r.status_code == 401
    assert r.json()["message"] != "Invalid email or password"


def test_protected_route_requires_token(client):
    assert client.get("/users").status_code == 401
    assert client.get("/users", headers={"Authorization": "Bearer garbage"}).status_code == 401
