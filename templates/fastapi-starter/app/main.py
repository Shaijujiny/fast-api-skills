import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import request_id_ctx, setup_logging


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = rid
        token = request_id_ctx.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = rid
        return response

    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
