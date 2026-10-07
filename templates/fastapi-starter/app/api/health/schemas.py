from app.schemas.common import BaseSchema


class HealthResponse(BaseSchema):
    database: str
