from fastapi import APIRouter

from app.api.health.schemas import HealthResponse
from app.api.health.service import HealthService
from app.core.deps import CommonDepsPublic
from app.core.i18n import get_messages
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=ApiResponse[HealthResponse])
async def health(deps: CommonDepsPublic) -> ApiResponse[HealthResponse]:
    """Liveness and database check. Public by design."""
    return await HealthService(deps).check()


@router.get("/live", response_model=ApiResponse[HealthResponse])
async def live(deps: CommonDepsPublic) -> ApiResponse[HealthResponse]:
    """Liveness: the process is up. Does not touch the database (container healthcheck)."""
    return ApiResponse[HealthResponse](
        message=get_messages(deps.lang).health_ok, data=HealthResponse(database="skipped")
    )


@router.get("/ready", response_model=ApiResponse[HealthResponse])
async def ready(deps: CommonDepsPublic) -> ApiResponse[HealthResponse]:
    """Readiness: the database answers. Route traffic only when this is 200."""
    return await HealthService(deps).check()
