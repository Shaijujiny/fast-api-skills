from tests.conftest import auth_headers, make_user

NEW = {"email": "New@Example.com", "name": "New", "password": "password123", "role": "staff"}


def test_create_get_list(client, admin_headers):
    r = client.post("/users", json=NEW, headers=admin_headers)
    assert r.status_code == 201
    user = r.json()["data"]
    assert user["email"] == "new@example.com" and user["role"] == "staff"
    assert "hashedPassword" not in user and "password" not in user

    assert client.get(f"/users/{user['publicId']}", headers=admin_headers).json()["data"]["name"] == "New"
    page = client.get("/users?limit=1", headers=admin_headers).json()["data"]
    assert page["totalCount"] == 2 and len(page["items"]) == 1
    assert client.get("/users?search=new", headers=admin_headers).json()["data"]["totalCount"] == 1


def test_duplicate_email_and_validation(client, admin_headers):
    assert client.post("/users", json=NEW, headers=admin_headers).status_code == 201
    dup = client.post("/users", json=NEW, headers=admin_headers)
    assert dup.status_code == 422 and dup.json()["code"] == "BUSINESS_422_EMAIL_EXISTS"
    short = client.post("/users", json={**NEW, "email": "z@example.com", "password": "short"}, headers=admin_headers)
    assert short.status_code == 422
    assert short.json()["message"] == "Password must be at least 8 characters"


def test_get_missing_user_404(client, admin_headers):
    assert client.get("/users/does-not-exist", headers=admin_headers).status_code == 404


def test_rbac_staff_can_view_but_not_create(client, db):
    make_user(db, "staff@example.com", role="staff")
    h = auth_headers(client, "staff@example.com")
    assert client.get("/users", headers=h).status_code == 200
    r = client.post("/users", json=NEW, headers=h)
    assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN_403"


def test_rbac_plain_user_forbidden(client, db):
    make_user(db, "u@example.com", role="user")
    assert client.get("/users", headers=auth_headers(client, "u@example.com")).status_code == 403
