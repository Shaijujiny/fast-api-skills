from pydantic import Field

from app.core.security import Action, Resource
from app.schemas.common import BaseSchema


class PermissionItem(BaseSchema):
    resource: Resource
    action: Action


class RoleResponse(BaseSchema):
    name: str
    description: str
    is_system: bool
    permissions: list[PermissionItem]


class RolePermissionsUpdateRequest(BaseSchema):
    permissions: list[PermissionItem] = Field(max_length=200)
