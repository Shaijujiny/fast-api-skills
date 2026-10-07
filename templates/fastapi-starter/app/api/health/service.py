from sqlalchemy import text

from app.api.health.schemas import HealthResponse
from app.core.deps import CommonDepsPublic
from app.core.i18n import get_messages
from app.schemas.common import ApiResponse


class HealthService:
    def __init__(self, deps: CommonDepsPublic) -> None:
        self.db = deps.db
        self.message = get_messages(deps.lang)

    async def check(self) -> ApiResponse[HealthResponse]:
        self.db.execute(text("SELECT 1"))
        return ApiResponse[HealthResponse](message=self.message.health_ok, data=HealthResponse(database="ok"))
