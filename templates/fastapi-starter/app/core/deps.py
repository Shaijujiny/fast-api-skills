"""Shared request dependencies (blueprint ch. 3.9, 4.3, 15.4)."""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.exceptions import AppException, ErrorCode
from app.core.i18n import get_messages, resolve_language
from app.core.security import Action, Resource, decode_access_token, has_permission
from app.models.user import User, UserStatus
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
    user = UserRepository(db).get_by_public_id(claims["sub"]) if claims else None
    if user is None:
        raise AppException(status.HTTP_401_UNAUTHORIZED, ErrorCode.AUTH_401_UNAUTHORIZED, msgs.unauthorized)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


@dataclass
class _Public:
    db: Session
    lang: str


@dataclass
class _Authed(_Public):
    current_user: User


def _public(db: DbSession, lang: Language) -> _Public:
    return _Public(db=db, lang=lang)


def _authed(db: DbSession, lang: Language, user: CurrentUser) -> _Authed:
    return _Authed(db=db, lang=lang, current_user=user)


CommonDepsPublic = Annotated[_Public, Depends(_public)]  # pre-auth routes: health, login
CommonDeps = Annotated[_Authed, Depends(_authed)]  # authenticated routes


def require_permission(resource: Resource, action: Action):
    """Route dependency: 401 if no valid token, 403 if inactive or not allowed. Fail closed."""

    def checker(user: CurrentUser, lang: Language) -> User:
        msgs = get_messages(lang)
        if user.status != UserStatus.ACTIVE.value:
            raise AppException(403, ErrorCode.FORBIDDEN_403_USER_INACTIVE, msgs.user_inactive)
        if not has_permission(user.role_enum, resource, action):
            raise AppException(403, ErrorCode.FORBIDDEN_403, msgs.forbidden)
        return user

    return checker
