from fastapi import APIRouter, Depends

from app.api.roles.schemas import RolePermissionsUpdateRequest, RoleResponse
from app.api.roles.service import RoleService
from app.core.deps import CommonDeps, require_permission
from app.core.security import Action, Resource
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get(
    "",
    response_model=ApiResponse[list[RoleResponse]],
    dependencies=[Depends(require_permission(Resource.ROLES, Action.VIEW))],
)
async def list_roles(deps: CommonDeps) -> ApiResponse[list[RoleResponse]]:
    """List roles with their permissions.

    ### Business Rules:
    - Requires `roles:view`.
    """
    return await RoleService(deps).list_roles()


@router.put(
    "/{name}/permissions",
    response_model=ApiResponse[RoleResponse],
    dependencies=[Depends(require_permission(Resource.ROLES, Action.EDIT))],
)
async def update_role_permissions(
    deps: CommonDeps, name: str, payload: RolePermissionsUpdateRequest
) -> ApiResponse[RoleResponse]:
    """Replace a role's permission set.

    ### Business Rules:
    - Requires `roles:edit`.
    - The `super_admin` role cannot be modified (400).
    - Takes effect immediately in this process; other workers within the permission cache TTL.
    """
    return await RoleService(deps).update_permissions(name, payload)
