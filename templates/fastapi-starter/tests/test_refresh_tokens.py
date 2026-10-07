from sqlalchemy import select

from app.models.refresh_token import RefreshToken
from tests.conftest import PASSWORD, auth_headers, login, make_user


def _tokens(client, email="a@example.com"):
    return login(client, email).json()["data"]


def _refresh(client, token):
    return client.post("/auth/refresh", json={"refreshToken": token})


def test_login_returns_refresh_and_stores_only_hash(client, db):
    make_user(db, "a@example.com")
    data = _tokens(client)
    assert data["refreshToken"] and data["accessToken"]
    row = db.execute(select(RefreshToken)).scalar_one()
    assert row.token_hash != data["refreshToken"] and len(row.token_hash) == 64


def test_refresh_rotates(client, db):
    make_user(db, "a@example.com")
    first = _tokens(client)["refreshToken"]
    r = _refresh(client, first)
    assert r.status_code == 200
    second = r.json()["data"]["refreshToken"]
    assert second != first
    rows = db.execute(select(RefreshToken).order_by(RefreshToken.id)).scalars().all()
    assert rows[0].revoked_at is not None and rows[0].replaced_by == rows[1].id and rows[1].revoked_at is None
    assert rows[0].family_id == rows[1].family_id
    # the new access token works
    h = {"Authorization": f"Bearer {r.json()['data']['accessToken']}"}
    assert client.get("/users", headers=h).status_code == 403  # plain user: authenticated but not allowed


def test_reuse_of_rotated_token_revokes_family(client, db):
    make_user(db, "a@example.com")
    first = _tokens(client)["refreshToken"]
    second = _refresh(client, first).json()["data"]["refreshToken"]
    reuse = _refresh(client, first)
    assert reuse.status_code == 401
    # the legitimate newest token of the family is now dead too
    assert _refresh(client, second).status_code == 401
    assert all(t.revoked_at is not None for t in db.execute(select(RefreshToken)).scalars())


def test_reuse_does_not_touch_other_families(client, db):
    make_user(db, "a@example.com")
    first = _tokens(client)["refreshToken"]
    other = _tokens(client)["refreshToken"]  # second device
    _refresh(client, first)
    assert _refresh(client, first).status_code == 401
    assert _refresh(client, other).status_code == 200


def test_unknown_and_expired_refresh_token(client, db):
    make_user(db, "a@example.com")
    assert _refresh(client, "nope").status_code == 401
    tok = _tokens(client)["refreshToken"]
    row = db.execute(select(RefreshToken)).scalar_one()
    from datetime import timedelta

    from app.utils import utc_now

    row.expires_at = utc_now() - timedelta(seconds=1)
    db.commit()
    assert _refresh(client, tok).status_code == 401


def test_logout_revokes_family(client, db):
    make_user(db, "a@example.com")
    first = _tokens(client)["refreshToken"]
    second = _refresh(client, first).json()["data"]["refreshToken"]
    assert client.post("/auth/logout", json={"refreshToken": second}).status_code == 200
    assert _refresh(client, second).status_code == 401
    assert client.post("/auth/logout", json={"refreshToken": "unknown"}).status_code == 200  # idempotent


def test_password_change_revokes_all_refresh_tokens(client, db):
    make_user(db, "a@example.com")
    t1, t2 = _tokens(client)["refreshToken"], _tokens(client)["refreshToken"]
    h = auth_headers(client, "a@example.com")
    bad = client.post(
        "/auth/change-password", json={"currentPassword": "wrong-one", "newPassword": "newpassword1"}, headers=h
    )
    assert bad.status_code == 400
    ok = client.post(
        "/auth/change-password", json={"currentPassword": PASSWORD, "newPassword": "newpassword1"}, headers=h
    )
    assert ok.status_code == 200
    assert _refresh(client, t1).status_code == 401 and _refresh(client, t2).status_code == 401
    assert login(client, "a@example.com").status_code == 401
    assert login(client, "a@example.com", "newpassword1").status_code == 200


def test_role_change_revokes_refresh_tokens(client, db):
    make_user(db, "admin@example.com", role="admin")
    target = make_user(db, "t@example.com")
    tok = _tokens(client, "t@example.com")["refreshToken"]
    h = auth_headers(client, "admin@example.com")
    r = client.patch(f"/users/{target.public_id}/role", json={"role": "staff"}, headers=h)
    assert r.status_code == 200 and r.json()["data"]["role"] == "staff"
    assert _refresh(client, tok).status_code == 401
