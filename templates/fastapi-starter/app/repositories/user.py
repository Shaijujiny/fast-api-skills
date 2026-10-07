"""The only place that queries the DB for users. Never commits: the service commits once."""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.common import PageParams


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_public_id(self, public_id: str, for_update: bool = False) -> User | None:
        stmt = select(User).where(User.public_id == public_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        return self.db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()

    def list(self, params: PageParams) -> tuple[Sequence[User], int]:
        stmt = select(User)
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
