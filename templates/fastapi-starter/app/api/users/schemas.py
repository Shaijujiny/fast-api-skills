from datetime import datetime

from pydantic import EmailStr, Field, SecretStr, field_validator

from app.models.user import Role, UserStatus
from app.schemas.common import BaseSchema


class UserCreateRequest(BaseSchema):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: SecretStr
    role: Role = Role.USER

    @field_validator("password")
    @classmethod
    def _password_length(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 8:
            raise ValueError("password_too_short")  # message key, resolved by the validation handler
        return v


class UserResponse(BaseSchema):
    """Client-facing id is public_id; the DB id and hashed_password never leave the server."""

    public_id: str
    email: str
    name: str
    role: Role
    status: UserStatus
    created_at: datetime
