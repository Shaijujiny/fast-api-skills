"""Password hashing, JWT, and the RBAC tables (blueprint ch. 8 and 15)."""

from datetime import timedelta
from enum import StrEnum

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.models.user import Role
from app.utils import utc_now

_hasher = PasswordHash.recommended()  # argon2


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _hasher.verify(plain, hashed)


def create_access_token(subject: str, role: str) -> tuple[str, int]:
    """Return (token, expires_in_seconds). Keep tokens short-lived; permissions are resolved server-side."""
    s = get_settings()
    ttl = timedelta(minutes=s.access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "exp": utc_now() + ttl}
    return jwt.encode(payload, s.secret_key.get_secret_value(), algorithm=s.jwt_algorithm), int(ttl.total_seconds())


def decode_access_token(token: str) -> dict | None:
    s = get_settings()
    try:
        return jwt.decode(token, s.secret_key.get_secret_value(), algorithms=[s.jwt_algorithm])
    except jwt.PyJWTError:
        return None


class Resource(StrEnum):  # code-level enum so typos fail at import time
    USERS = "users"


class Action(StrEnum):
    VIEW = "view"
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    EXPORT = "export"  # its own action: viewing a list != downloading it


# Role -> allowed (resource, action). Move to roles/permissions tables when roles must be editable at runtime.
ROLE_PERMISSIONS: dict[Role, set[tuple[Resource, Action]]] = {
    Role.ADMIN: {(Resource.USERS, a) for a in Action},
    Role.STAFF: {(Resource.USERS, Action.VIEW)},
    Role.USER: set(),
}


def has_permission(role: Role, resource: Resource, action: Action) -> bool:
    return (resource, action) in ROLE_PERMISSIONS.get(role, set())
