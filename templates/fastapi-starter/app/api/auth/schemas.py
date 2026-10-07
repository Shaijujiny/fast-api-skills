from pydantic import EmailStr, SecretStr

from app.schemas.common import BaseSchema


class LoginRequest(BaseSchema):
    email: EmailStr
    password: SecretStr  # hidden in repr/logs


class TokenResponse(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
