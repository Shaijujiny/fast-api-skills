"""The only place that queries the DB for users. Never commits: the service commits once."""

from collections.abc import Sequence

from sqlalchemy import func, select

from app.models.user import User
from app.repositories.base import Scope, ScopedRepository
from app.schemas.common import PageParams


class UserRepository(ScopedRepository):
    scope_model = User

    def get_for_auth(self, public_id: str) -> User | None:
        """Identity lookup for the token subject. NOT tenant-scoped: never use for data access."""
        return self.db.execute(select(User).where(User.public_id == public_id)).scalar_one_or_none()

    def get_for_auth_by_id(self, user_id: int) -> User | None:
        """Not tenant-scoped (token owner lookup)."""
        return self.db.get(User, user_id)

    def get_by_public_id(self, public_id: str, scope: Scope, for_update: bool = False) -> User | None:
        stmt = self.scoped(select(User).where(User.public_id == public_id), scope)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        """Global on purpose: emails are unique across tenants and login happens before any scope exists."""
        return self.db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()

    def list(self, params: PageParams, scope: Scope) -> tuple[Sequence[User], int]:
        stmt = self.scoped(select(User), scope)
        if params.search:
            term = params.search.replace("%", r"\%").replace("_", r"\_")
            stmt = stmt.where(User.name.ilike(f"%{term}%", escape="\\") | User.email.ilike(f"%{term}%", escape="\\"))
        total = self.db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        rows = self.db.execute(stmt.order_by(User.id).offset(params.offset).limit(params.limit)).scalars().all()
        return rows, total

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()  # populate ids; the service commits
        return user
