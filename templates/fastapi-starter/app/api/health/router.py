from fastapi import APIRouter

from app.api.health.schemas import HealthResponse
from app.api.health.service import HealthService
from app.core.deps import CommonDepsPublic
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=ApiResponse[HealthResponse])
async def health(deps: CommonDepsPublic) -> ApiResponse[HealthResponse]:
    """Liveness and database check. Public by design."""
    return await HealthService(deps).check()
