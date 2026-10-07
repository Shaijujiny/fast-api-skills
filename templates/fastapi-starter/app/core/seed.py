"""Default roles and permissions. Idempotent; the Alembic migration seeds the same data.

Run against a real DB with `python -m app.core.seed` (e.g. after `make migrate` on a fresh install).
Existing roles keep the permissions an admin edited; only missing roles/permissions are added.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import Action, Resource
from app.models.rbac import PermissionModel, RoleModel

ALL = {(r.value, a.value) for r in Resource for a in Action}

DEFAULT_ROLES: dict[str, tuple[str, set[tuple[str, str]]]] = {
    "super_admin": ("Cross-tenant administrator", ALL),
    "admin": ("Organization administrator", {("users", a.value) for a in Action} | {("roles", "view")}),
    "staff": ("Read-only staff", {("users", "view")}),
    "user": ("Regular user, no admin access", set()),
}


def seed_defaults(db: Session) -> None:
    perms = {(p.resource, p.action): p for p in db.execute(select(PermissionModel)).scalars()}
    for key in sorted(ALL - perms.keys()):
        perms[key] = PermissionModel(resource=key[0], action=key[1])
        db.add(perms[key])
    existing = {r.name for r in db.execute(select(RoleModel)).scalars()}
    for name, (description, pairs) in DEFAULT_ROLES.items():
        if name not in existing:
            db.add(
                RoleModel(
                    name=name, description=description, is_system=True, permissions=[perms[k] for k in sorted(pairs)]
                )
            )
    db.commit()


if __name__ == "__main__":
    from app.database import SessionLocal

    with SessionLocal() as session:
        seed_defaults(session)
