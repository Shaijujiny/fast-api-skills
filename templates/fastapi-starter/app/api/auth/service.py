import uuid
from datetime import timedelta
from functools import lru_cache

from fastapi import status

from app.api.auth.schemas import ChangePasswordRequest, LoginRequest, RefreshRequest, TokenResponse
from app.core.config import get_settings
from app.core.deps import CommonDeps, CommonDepsPublic
from app.core.exceptions import AppException, ErrorCode
from app.core.i18n import get_messages
from app.core.rate_limit import enforce_rate_limit
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserStatus
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.common import ApiResponse
from app.utils import as_utc, utc_now


@lru_cache
def _dummy_hash() -> str:
    return hash_password("not-a-real-password")  # burned when the user is unknown, to equalize timing


class AuthService:
    def __init__(self, deps: CommonDepsPublic | CommonDeps) -> None:
        self.deps = deps
        self.db = deps.db
        self.message = get_messages(deps.lang)
        self.users = UserRepository(self.db)
        self.tokens = RefreshTokenRepository(self.db)
        self.settings = get_settings()

    # ---- helpers -------------------------------------------------------------------------------------------
    def _invalid_credentials(self) -> AppException:
        return AppException(
            status.HTTP_401_UNAUTHORIZED, ErrorCode.AUTH_401_INVALID_CREDENTIALS, self.message.invalid_credentials
        )

    def _invalid_refresh(self) -> AppException:
        return AppException(
            status.HTTP_401_UNAUTHORIZED, ErrorCode.AUTH_401_UNAUTHORIZED, self.message.invalid_refresh_token
        )

    def _issue(self, user: User, family_id: str | None = None) -> tuple[TokenResponse, RefreshToken]:
        raw, digest = generate_refresh_token()
        row = self.tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=digest,
                family_id=family_id or str(uuid.uuid4()),
                expires_at=utc_now() + timedelta(days=self.settings.refresh_token_expire_days),
                user_agent=self.deps.user_agent,
                ip=self.deps.ip,
            )
        )
        access, expires_in = create_access_token(user.public_id, user.role)
        return TokenResponse(access_token=access, refresh_token=raw, expires_in=expires_in), row

    def _commit(self) -> None:
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    # ---- use cases -----------------------------------------------------------------------------------------
    async def login(self, payload: LoginRequest) -> ApiResponse[TokenResponse]:
        s, email = self.settings, payload.email.lower()
        enforce_rate_limit(f"login:{self.deps.ip}:{email}", s.login_rate_limit, s.login_rate_window_seconds)

        user = self.users.get_by_email(email)
        now = utc_now()
        locked = user is not None and user.locked_until is not None and as_utc(user.locked_until) > now
        # Always run one hash verification; unknown, locked and wrong-password cases are indistinguishable.
        password_ok = verify_password(
            payload.password.get_secret_value(), user.hashed_password if user else _dummy_hash()
        )
        if user is None or locked or not password_ok:
            if user is not None and not locked:
                user.failed_login_count += 1
                if user.failed_login_count >= s.login_max_failed_attempts:
                    user.locked_until = now + timedelta(minutes=s.login_lockout_minutes)
                    user.failed_login_count = 0
                self._commit()  # persist the counter even though we raise
            raise self._invalid_credentials()
        if user.status != UserStatus.ACTIVE.value:
            raise AppException(
                status.HTTP_403_FORBIDDEN, ErrorCode.FORBIDDEN_403_USER_INACTIVE, self.message.user_inactive
            )
        user.failed_login_count, user.locked_until = 0, None
        data, _ = self._issue(user)
        self._commit()
        return ApiResponse[TokenResponse](message=self.message.login_success, data=data)

    async def refresh(self, payload: RefreshRequest) -> ApiResponse[TokenResponse]:
        row = self.tokens.get_by_hash(hash_refresh_token(payload.refresh_token.get_secret_value()))
        if row is None:
            raise self._invalid_refresh()
        if row.revoked_at is not None:
            # A rotated/revoked token came back: assume theft, kill every token of the family.
            self.tokens.revoke_family(row.family_id)
            self._commit()
            raise self._invalid_refresh()
        if as_utc(row.expires_at) <= utc_now():
            raise self._invalid_refresh()
        user = self.users.get_for_auth_by_id(row.user_id)
        if user is None or user.status != UserStatus.ACTIVE.value:
            self.tokens.revoke_family(row.family_id)
            self._commit()
            raise self._invalid_refresh()
        data, new_row = self._issue(user, family_id=row.family_id)
        row.revoked_at, row.replaced_by = utc_now(), new_row.id
        self._commit()
        return ApiResponse[TokenResponse](message=self.message.token_refreshed, data=data)

    async def logout(self, payload: RefreshRequest) -> ApiResponse[None]:
        row = self.tokens.get_by_hash(hash_refresh_token(payload.refresh_token.get_secret_value()))
        if row is not None:  # idempotent: unknown token still answers 200
            self.tokens.revoke_family(row.family_id)
            self._commit()
        return ApiResponse[None](message=self.message.logout_success)

    async def change_password(self, payload: ChangePasswordRequest) -> ApiResponse[None]:
        user = self.deps.current_user  # type: ignore[union-attr]
        if not verify_password(payload.current_password.get_secret_value(), user.hashed_password):
            raise AppException(400, ErrorCode.BAD_REQUEST_400, self.message.invalid_current_password)
        user.hashed_password = hash_password(payload.new_password.get_secret_value())
        self.tokens.revoke_all_for_user(user.id)  # every session must log in again
        self._commit()
        return ApiResponse[None](message=self.message.password_changed)
