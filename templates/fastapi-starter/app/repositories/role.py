from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rbac import PermissionModel, RoleModel


class RoleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> Sequence[RoleModel]:
        return self.db.execute(select(RoleModel).order_by(RoleModel.id)).scalars().all()

    def get_by_name(self, name: str) -> RoleModel | None:
        return self.db.execute(select(RoleModel).where(RoleModel.name == name)).scalar_one_or_none()

    def permission_pairs(self, name: str) -> frozenset[tuple[str, str]]:
        role = self.get_by_name(name)
        return frozenset((p.resource, p.action) for p in role.permissions) if role else frozenset()

    def permissions_for(self, pairs: set[tuple[str, str]]) -> Sequence[PermissionModel]:
        rows = self.db.execute(select(PermissionModel)).scalars().all()
        by_key = {(p.resource, p.action): p for p in rows}
        return [by_key[k] for k in sorted(pairs) if k in by_key]
