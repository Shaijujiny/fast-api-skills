from fastapi import APIRouter

from app.api.auth.schemas import LoginRequest, TokenResponse
from app.api.auth.service import AuthService
from app.core.deps import CommonDepsPublic
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(deps: CommonDepsPublic, payload: LoginRequest) -> ApiResponse[TokenResponse]:
    """Exchange email and password for a JWT access token.

    ### Business Rules:
    - Public (pre-auth) route; put a rate limit in front of it in production.
    - Inactive users cannot log in.
    """
    return await AuthService(deps).login(payload)
