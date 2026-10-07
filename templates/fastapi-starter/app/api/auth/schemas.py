from pydantic import EmailStr, SecretStr, field_validator

from app.schemas.common import BaseSchema


class LoginRequest(BaseSchema):
    email: EmailStr
    password: SecretStr  # hidden in repr/logs


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseSchema):
    refresh_token: SecretStr


class ChangePasswordRequest(BaseSchema):
    current_password: SecretStr
    new_password: SecretStr

    @field_validator("new_password")
    @classmethod
    def _password_length(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 8:
            raise ValueError("password_too_short")
        return v
