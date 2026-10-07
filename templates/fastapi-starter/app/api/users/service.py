from fastapi import status

from app.api.users.schemas import UserCreateRequest, UserResponse, UserRoleUpdateRequest
from app.core.deps import CommonDeps
from app.core.exceptions import AppException, ErrorCode
from app.core.i18n import get_messages
from app.core.security import hash_password
from app.models.user import Role, User, UserStatus
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.common import ApiResponse, PageData, PageParams


class UserService:
    def __init__(self, deps: CommonDeps) -> None:
        self.db = deps.db
        self.current_user = deps.current_user
        self.scope = deps.scope
        self.message = get_messages(deps.lang)
        self.repo = UserRepository(self.db)

    def _check_can_assign(self, role: Role) -> None:
        """Only a super_admin may hand out super_admin (no privilege escalation by org admins)."""
        if role == Role.SUPER_ADMIN and not self.scope.is_super:
            raise AppException(status.HTTP_403_FORBIDDEN, ErrorCode.FORBIDDEN_403, self.message.forbidden)

    async def list_users(self, params: PageParams) -> ApiResponse[PageData[UserResponse]]:
        rows, total = self.repo.list(params, self.scope)
        data = PageData[UserResponse](items=[UserResponse.model_validate(r) for r in rows], total_count=total)
        return ApiResponse[PageData[UserResponse]](message=self.message.users_fetched, data=data)

    async def get_user(self, public_id: str) -> ApiResponse[UserResponse]:
        user = self.repo.get_by_public_id(public_id, self.scope)
        if user is None:
            raise AppException(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND_404, self.message.user_not_found)
        return ApiResponse[UserResponse](message=self.message.user_fetched, data=UserResponse.model_validate(user))

    async def create_user(self, payload: UserCreateRequest) -> ApiResponse[UserResponse]:
        email = payload.email.lower()
        if self.repo.get_by_email(email):
            raise AppException(422, ErrorCode.BUSINESS_422_EMAIL_EXISTS, self.message.email_exists)
        self._check_can_assign(payload.role)
        user = self.repo.add(
            User(
                email=email,
                name=payload.name,
                hashed_password=hash_password(payload.password.get_secret_value()),
                role=payload.role.value,
                status=UserStatus.ACTIVE.value,
                organization_id=self.current_user.organization_id,  # new users join the creator's tenant
            )
        )
        try:
            self.db.commit()  # commit once, at the end of the unit of work
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(user)
        return ApiResponse[UserResponse](
            status_code=status.HTTP_201_CREATED,
            message=self.message.user_created,
            data=UserResponse.model_validate(user),
        )

    async def update_role(self, public_id: str, payload: UserRoleUpdateRequest) -> ApiResponse[UserResponse]:
        user = self.repo.get_by_public_id(public_id, self.scope, for_update=True)
        if user is None:
            raise AppException(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND_404, self.message.user_not_found)
        self._check_can_assign(payload.role)
        if user.role == Role.SUPER_ADMIN.value and not self.scope.is_super:
            raise AppException(status.HTTP_403_FORBIDDEN, ErrorCode.FORBIDDEN_403, self.message.forbidden)
        user.role = payload.role.value
        RefreshTokenRepository(self.db).revoke_all_for_user(user.id)  # a role change ends existing sessions
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(user)
        return ApiResponse[UserResponse](message=self.message.user_role_updated, data=UserResponse.model_validate(user))
