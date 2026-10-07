from fastapi import APIRouter, Depends

from app.api.auth.schemas import ChangePasswordRequest, LoginRequest, RefreshRequest, TokenResponse
from app.api.auth.service import AuthService
from app.core.config import get_settings
from app.core.deps import CommonDeps, CommonDepsPublic
from app.core.rate_limit import rate_limit
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(deps: CommonDepsPublic, payload: LoginRequest) -> ApiResponse[TokenResponse]:
    """Exchange email and password for an access token and a refresh token.

    ### Business Rules:
    - Public (pre-auth) route; rate limited per IP + email (429 with `Retry-After`).
    - Repeated failures lock the account temporarily; unknown email, wrong password and locked account
      all return the same 401.
    - Inactive users cannot log in.
    """
    return await AuthService(deps).login(payload)


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
    dependencies=[
        Depends(
            rate_limit(
                "auth:refresh",
                lambda: get_settings().refresh_rate_limit,
                lambda: get_settings().refresh_rate_window_seconds,
            )
        )
    ],
)
async def refresh(deps: CommonDepsPublic, payload: RefreshRequest) -> ApiResponse[TokenResponse]:
    """Rotate a refresh token: the old one is revoked and a new pair is issued.

    ### Business Rules:
    - Rate limited per IP.
    - Presenting an already-used (revoked) refresh token revokes the whole token family.
    """
    return await AuthService(deps).refresh(payload)


@router.post("/logout", response_model=ApiResponse[None])
async def logout(deps: CommonDepsPublic, payload: RefreshRequest) -> ApiResponse[None]:
    """Revoke the refresh-token family of the given token (idempotent).

    ### Business Rules:
    - The access token stays valid until it expires (short lifetime).
    """
    return await AuthService(deps).logout(payload)


@router.post("/change-password", response_model=ApiResponse[None])
async def change_password(deps: CommonDeps, payload: ChangePasswordRequest) -> ApiResponse[None]:
    """Change the caller's password.

    ### Business Rules:
    - Requires the current password.
    - Revokes all of the user's refresh tokens.
    """
    return await AuthService(deps).change_password(payload)
