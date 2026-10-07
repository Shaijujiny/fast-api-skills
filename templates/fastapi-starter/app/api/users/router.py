from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.users.schemas import UserCreateRequest, UserResponse, UserRoleUpdateRequest
from app.api.users.service import UserService
from app.core.deps import CommonDeps, require_permission
from app.core.security import Action, Resource
from app.schemas.common import ApiResponse, PageData, PageParams

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=ApiResponse[PageData[UserResponse]],
    dependencies=[Depends(require_permission(Resource.USERS, Action.VIEW))],
)
async def list_users(deps: CommonDeps, params: Annotated[PageParams, Depends()]) -> ApiResponse[PageData[UserResponse]]:
    """List users.

    ### Business Rules:
    - Requires `users:view`.
    - Tenant scoped: only the caller's organization (super_admin: all).
    """
    return await UserService(deps).list_users(params)


@router.post(
    "",
    status_code=201,
    response_model=ApiResponse[UserResponse],
    dependencies=[Depends(require_permission(Resource.USERS, Action.CREATE))],
)
async def create_user(deps: CommonDeps, payload: UserCreateRequest) -> ApiResponse[UserResponse]:
    """Create a user.

    ### Business Rules:
    - Requires `users:create`.
    - Email must be unique (422 otherwise).
    """
    return await UserService(deps).create_user(payload)


@router.get(
    "/{public_id}",
    response_model=ApiResponse[UserResponse],
    dependencies=[Depends(require_permission(Resource.USERS, Action.VIEW))],
)
async def get_user(deps: CommonDeps, public_id: str) -> ApiResponse[UserResponse]:
    """Get one user by public id.

    ### Business Rules:
    - Requires `users:view`.
    - A user in another organization is 404 (not 403), unless the caller is super_admin.
    """
    return await UserService(deps).get_user(public_id)


@router.patch(
    "/{public_id}/role",
    response_model=ApiResponse[UserResponse],
    dependencies=[Depends(require_permission(Resource.USERS, Action.EDIT))],
)
async def update_user_role(
    deps: CommonDeps, public_id: str, payload: UserRoleUpdateRequest
) -> ApiResponse[UserResponse]:
    """Change a user's role.

    ### Business Rules:
    - Requires `users:edit`; the user must be in the caller's scope (404 otherwise).
    - Only a super_admin can grant or change super_admin.
    - Revokes all of the user's refresh tokens.
    """
    return await UserService(deps).update_role(public_id, payload)
