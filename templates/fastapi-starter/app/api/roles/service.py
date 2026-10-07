from fastapi import status

from app.api.roles.schemas import PermissionItem, RolePermissionsUpdateRequest, RoleResponse
from app.core.deps import CommonDeps
from app.core.exceptions import AppException, ErrorCode
from app.core.i18n import get_messages
from app.core.security import permission_resolver
from app.models.rbac import RoleModel
from app.models.user import Role
from app.repositories.role import RoleRepository
from app.schemas.common import ApiResponse


def _to_response(role: RoleModel) -> RoleResponse:
    items = [PermissionItem(resource=p.resource, action=p.action) for p in role.permissions]
    return RoleResponse(name=role.name, description=role.description, is_system=role.is_system, permissions=items)


class RoleService:
    def __init__(self, deps: CommonDeps) -> None:
        self.db = deps.db
        self.message = get_messages(deps.lang)
        self.repo = RoleRepository(self.db)

    async def list_roles(self) -> ApiResponse[list[RoleResponse]]:
        return ApiResponse[list[RoleResponse]](
            message=self.message.roles_fetched, data=[_to_response(r) for r in self.repo.list()]
        )

    async def update_permissions(self, name: str, payload: RolePermissionsUpdateRequest) -> ApiResponse[RoleResponse]:
        role = self.repo.get_by_name(name)
        if role is None:
            raise AppException(status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND_404, self.message.role_not_found)
        if role.name == Role.SUPER_ADMIN.value:  # never lock the platform out of its own admin role
            raise AppException(status.HTTP_400_BAD_REQUEST, ErrorCode.BAD_REQUEST_400, self.message.role_locked)
        pairs = {(p.resource.value, p.action.value) for p in payload.permissions}
        role.permissions = self.repo.permissions_for(pairs)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        permission_resolver.invalidate(role.name)  # after commit, so the next read sees the new rows
        self.db.refresh(role)
        return ApiResponse[RoleResponse](message=self.message.role_updated, data=_to_response(role))
