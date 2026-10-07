from fastapi import status

from app.api.auth.schemas import LoginRequest, TokenResponse
from app.core.deps import CommonDepsPublic
from app.core.exceptions import AppException, ErrorCode
from app.core.i18n import get_messages
from app.core.security import create_access_token, verify_password
from app.models.user import UserStatus
from app.repositories.user import UserRepository
from app.schemas.common import ApiResponse


class AuthService:
    def __init__(self, deps: CommonDepsPublic) -> None:
        self.db = deps.db
        self.message = get_messages(deps.lang)
        self.users = UserRepository(self.db)

    async def login(self, payload: LoginRequest) -> ApiResponse[TokenResponse]:
        user = self.users.get_by_email(payload.email)
        # Same error for unknown email and wrong password: do not reveal which one failed.
        if user is None or not verify_password(payload.password.get_secret_value(), user.hashed_password):
            raise AppException(
                status.HTTP_401_UNAUTHORIZED, ErrorCode.AUTH_401_INVALID_CREDENTIALS, self.message.invalid_credentials
            )
        if user.status != UserStatus.ACTIVE.value:
            raise AppException(
                status.HTTP_403_FORBIDDEN, ErrorCode.FORBIDDEN_403_USER_INACTIVE, self.message.user_inactive
            )
        token, expires_in = create_access_token(user.public_id, user.role)
        return ApiResponse[TokenResponse](
            message=self.message.login_success, data=TokenResponse(access_token=token, expires_in=expires_in)
        )
