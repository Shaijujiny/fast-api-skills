import uuid
from enum import StrEnum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Role(StrEnum):
    ADMIN = "admin"
    STAFF = "staff"
    USER = "user"


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=Role.USER.value)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=UserStatus.ACTIVE.value, index=True)

    @property
    def role_enum(self) -> Role:
        return Role(self.role)
