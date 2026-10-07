"""Tenant scoping helper (blueprint ch. 15). Every tenant-owned repository extends `ScopedRepository`."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class Scope:
    """Who is asking, as far as data visibility goes. Built once per request in `deps.get_scope`."""

    organization_id: int | None
    is_super: bool = False  # super_admin sees every organization


class ScopedRepository:
    """Subclass and set `scope_model` to the mapped class that has an `organization_id` column.

    Call `self.scoped(stmt, scope)` in EVERY read (list, get, count, exists). A row outside the caller's
    organization then simply does not exist: services answer 404, never 403 (do not confirm it exists).
    """

    scope_model: Any  # a mapped class with an `organization_id` column

    def __init__(self, db: Session) -> None:
        self.db = db

    def scoped(self, stmt: Select, scope: Scope) -> Select:
        if scope.is_super:
            return stmt
        # organization_id None means "unassigned": those callers only see unassigned rows (IS NULL).
        return stmt.where(self.scope_model.organization_id == scope.organization_id)
