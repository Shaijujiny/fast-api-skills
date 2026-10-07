"""Shared request dependencies (blueprint ch. 3.9, 4.3, 15.4)."""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.exceptions import AppException, ErrorCode
from app.core.i18n import get_messages, resolve_language
from app.core.rate_limit import client_ip
from app.core.security import Action, Resource, decode_access_token, has_permission
from app.models.user import Role, User, UserStatus
from app.repositories.base import Scope
from app.repositories.user import UserRepository

_bearer = HTTPBearer(auto_error=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_language(accept_language: Annotated[str | None, Header()] = None) -> str:
    return resolve_language(accept_language)


DbSession = Annotated[Session, Depends(get_db)]
Language = Annotated[str, Depends(get_language)]


def get_current_user(
    db: DbSession,
    lang: Language,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    msgs = get_messages(lang)
    claims = decode_access_token(creds.credentials) if creds else None
    user = UserRepository(db).get_for_auth(claims["sub"]) if claims else None
    if user is None:
        raise AppException(status.HTTP_401_UNAUTHORIZED, ErrorCode.AUTH_401_UNAUTHORIZED, msgs.unauthorized)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_scope(user: CurrentUser) -> Scope:
    """Tenant scope of the caller: their organization, or everything for super_admin."""
    return Scope(organization_id=user.organization_id, is_super=user.role == Role.SUPER_ADMIN.value)


CurrentScope = Annotated[Scope, Depends(get_scope)]


@dataclass
class _Public:
    db: Session
    lang: str
    ip: str = "unknown"
    user_agent: str | None = None


@dataclass(kw_only=True)
class _Authed(_Public):
    current_user: User
    scope: Scope


def _public(db: DbSession, lang: Language, request: Request) -> _Public:
    ua = request.headers.get("user-agent")
    return _Public(db=db, lang=lang, ip=client_ip(request), user_agent=ua[:255] if ua else None)


def _authed(db: DbSession, lang: Language, user: CurrentUser, scope: CurrentScope, request: Request) -> _Authed:
    ua = request.headers.get("user-agent")
    return _Authed(
        db=db, lang=lang, ip=client_ip(request), user_agent=ua[:255] if ua else None, current_user=user, scope=scope
    )


CommonDepsPublic = Annotated[_Public, Depends(_public)]  # pre-auth routes: health, login
CommonDeps = Annotated[_Authed, Depends(_authed)]  # authenticated routes


def require_permission(resource: Resource, action: Action):
    """Route dependency: 401 if no valid token, 403 if inactive or not allowed. Fail closed."""

    def checker(user: CurrentUser, db: DbSession, lang: Language) -> User:
        msgs = get_messages(lang)
        if user.status != UserStatus.ACTIVE.value:
            raise AppException(403, ErrorCode.FORBIDDEN_403_USER_INACTIVE, msgs.user_inactive)
        if not has_permission(db, user.role, resource, action):
            raise AppException(403, ErrorCode.FORBIDDEN_403, msgs.forbidden)
        return user

    return checker
