"""Password hashing, JWT, refresh-token helpers and the cached RBAC resolver (blueprint ch. 8 and 15)."""

import hashlib
import secrets
import threading
import time
from datetime import timedelta
from enum import StrEnum

import jwt
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.role import RoleRepository
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


def generate_refresh_token() -> tuple[str, str]:
    """Return (raw_token, sha256_hash). Only the hash is stored; the raw token goes to the client once."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()  # high-entropy random token: a fast hash is sufficient


class Resource(StrEnum):  # code-level enum so typos fail at import time
    USERS = "users"
    ROLES = "roles"


class Action(StrEnum):
    VIEW = "view"
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    EXPORT = "export"  # its own action: viewing a list != downloading it


class PermissionResolver:
    """role name -> {(resource, action)} read from the roles/permissions tables, cached with a TTL.

    The cache is per process: `invalidate()` makes a role change visible immediately here, other workers
    pick it up within `permission_cache_ttl_seconds`. Unknown role -> empty set (fail closed).
    """

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, frozenset[tuple[str, str]]]] = {}
        self._lock = threading.Lock()

    def get(self, db: Session, role: str) -> frozenset[tuple[str, str]]:
        now = time.monotonic()
        with self._lock:
            hit = self._cache.get(role)
            if hit and hit[0] > now:
                return hit[1]
        pairs = RoleRepository(db).permission_pairs(role)
        ttl = get_settings().permission_cache_ttl_seconds
        with self._lock:
            self._cache[role] = (now + ttl, pairs)
        return pairs

    def invalidate(self, role: str | None = None) -> None:
        with self._lock:
            if role is None:
                self._cache.clear()
            else:
                self._cache.pop(role, None)


permission_resolver = PermissionResolver()


def has_permission(db: Session, role: str, resource: Resource, action: Action) -> bool:
    return (resource.value, action.value) in permission_resolver.get(db, role)
