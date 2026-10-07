from sqlalchemy import select

from app.core.security import permission_resolver
from app.models.rbac import PermissionModel, RoleModel
from tests.conftest import auth_headers, make_org, make_user


def test_super_admin_lists_roles_and_admin_can_view_only(client, db):
    make_user(db, "root@example.com", role="super_admin")
    make_user(db, "admin@example.com", role="admin")
    roles = client.get("/roles", headers=auth_headers(client, "root@example.com")).json()["data"]
    assert {r["name"] for r in roles} == {"super_admin", "admin", "staff", "user"}
    h = auth_headers(client, "admin@example.com")
    assert client.get("/roles", headers=h).status_code == 200
    r = client.put("/roles/staff/permissions", json={"permissions": []}, headers=h)
    assert r.status_code == 403


def test_role_permission_change_takes_effect(client, db):
    make_user(db, "root@example.com", role="super_admin")
    make_user(db, "staff@example.com", role="staff")
    root, staff = auth_headers(client, "root@example.com"), auth_headers(client, "staff@example.com")
    assert client.get("/users", headers=staff).status_code == 200  # warms the cache
    r = client.put("/roles/staff/permissions", json={"permissions": []}, headers=root)
    assert r.status_code == 200 and r.json()["data"]["permissions"] == []
    assert client.get("/users", headers=staff).status_code == 403  # revoked immediately
    grant = [{"resource": "users", "action": "view"}, {"resource": "users", "action": "create"}]
    assert client.put("/roles/staff/permissions", json={"permissions": grant}, headers=root).status_code == 200
    body = {"email": "n@example.com", "name": "N", "password": "password123"}
    assert client.post("/users", json=body, headers=staff).status_code == 201


def test_permissions_come_from_tables(client, db):
    """Direct table edit + cache invalidation (what another worker sees after the TTL)."""
    make_user(db, "u@example.com", role="user")
    h = auth_headers(client, "u@example.com")
    assert client.get("/users", headers=h).status_code == 403
    perm = db.execute(select(PermissionModel).filter_by(resource="users", action="view")).scalar_one()
    role = db.execute(select(RoleModel).filter_by(name="user")).scalar_one()
    role.permissions.append(perm)
    db.commit()
    permission_resolver.invalidate()
    assert client.get("/users", headers=h).status_code == 200


def test_super_admin_role_locked_and_unknown_role(client, db):
    make_user(db, "root@example.com", role="super_admin")
    h = auth_headers(client, "root@example.com")
    assert client.put("/roles/super_admin/permissions", json={"permissions": []}, headers=h).status_code == 400
    assert client.put("/roles/nope/permissions", json={"permissions": []}, headers=h).status_code == 404
    bad = client.put("/roles/staff/permissions", json={"permissions": [{"resource": "x", "action": "view"}]}, headers=h)
    assert bad.status_code == 422


def test_unknown_role_name_fails_closed(client, db):
    make_user(db, "w@example.com", role="ghost-role")
    assert client.get("/users", headers=auth_headers(client, "w@example.com")).status_code == 403


def test_tenant_isolation(client, db):
    a, b = make_org(db, "A"), make_org(db, "B")
    make_user(db, "admin-a@example.com", role="admin", org=a)
    make_user(db, "user-a@example.com", org=a)
    ub = make_user(db, "user-b@example.com", org=b)
    make_user(db, "root@example.com", role="super_admin")
    ha = auth_headers(client, "admin-a@example.com")

    page = client.get("/users", headers=ha).json()["data"]
    assert {u["email"] for u in page["items"]} == {"admin-a@example.com", "user-a@example.com"}
    assert page["totalCount"] == 2
    assert client.get("/users?search=user-b", headers=ha).json()["data"]["totalCount"] == 0
    cross = client.get(f"/users/{ub.public_id}", headers=ha)
    assert cross.status_code == 404 and cross.json()["code"] == "NOT_FOUND_404"  # not 403
    assert client.patch(f"/users/{ub.public_id}/role", json={"role": "staff"}, headers=ha).status_code == 404

    hroot = auth_headers(client, "root@example.com")
    assert client.get(f"/users/{ub.public_id}", headers=hroot).status_code == 200
    assert client.get("/users", headers=hroot).json()["data"]["totalCount"] == 4


def test_created_user_joins_creator_org_and_no_escalation(client, db):
    a = make_org(db, "A")
    admin = make_user(db, "admin-a@example.com", role="admin", org=a)
    h = auth_headers(client, "admin-a@example.com")
    body = {"email": "n@example.com", "name": "N", "password": "password123"}
    created = client.post("/users", json=body, headers=h).json()["data"]
    from app.models.user import User

    assert (
        db.execute(select(User).filter_by(public_id=created["publicId"])).scalar_one().organization_id
        == admin.organization_id
    )
    esc = client.post("/users", json={**body, "email": "e@example.com", "role": "super_admin"}, headers=h)
    assert esc.status_code == 403
