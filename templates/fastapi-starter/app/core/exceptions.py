"""AppException / ErrorCode and the global handlers (blueprint ch. 5.6)."""

from enum import StrEnum

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.i18n import get_messages, resolve_language
from app.core.logging import get_logger
from app.schemas.common import ApiResponse

logger = get_logger(__name__)


class ErrorCode(StrEnum):
    SUCCESS = "SUCCESS"
    BAD_REQUEST_400 = "BAD_REQUEST_400"
    AUTH_401_INVALID_CREDENTIALS = "AUTH_401_INVALID_CREDENTIALS"
    AUTH_401_UNAUTHORIZED = "AUTH_401_UNAUTHORIZED"
    FORBIDDEN_403 = "FORBIDDEN_403"
    FORBIDDEN_403_USER_INACTIVE = "FORBIDDEN_403_USER_INACTIVE"
    NOT_FOUND_404 = "NOT_FOUND_404"
    BUSINESS_422_EMAIL_EXISTS = "BUSINESS_422_EMAIL_EXISTS"
    VALIDATION_422 = "VALIDATION_422"
    SYSTEM_500 = "SYSTEM_500"


class AppException(Exception):
    """Raise from services. `message` is already localized (use self.message.<key>)."""

    def __init__(self, status_code: int, code: ErrorCode, message: str, data=None, headers: dict | None = None):
        super().__init__(message)
        self.status_code, self.code, self.message, self.data, self.headers = status_code, code, message, data, headers


def _error(status_code: int, code: ErrorCode, message: str, data=None, headers: dict | None = None) -> JSONResponse:
    body = ApiResponse[None](status="0", status_code=status_code, code=code, message=message, data=data)
    return JSONResponse(body.model_dump(by_alias=True, mode="json"), status_code=status_code, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def _app(_: Request, exc: AppException):
        return _error(exc.status_code, exc.code, exc.message, exc.data, exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        msgs = get_messages(resolve_language(request.headers.get("accept-language")))
        if exc.status_code == 404:
            return _error(404, ErrorCode.NOT_FOUND_404, msgs.not_found)
        return _error(exc.status_code, ErrorCode.BAD_REQUEST_400, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        msgs = get_messages(resolve_language(request.headers.get("accept-language")))
        # Validators raise ValueError("<message_key>"); resolve the first one, else a generic message.
        raw = str(exc.errors()[0].get("msg", "")).removeprefix("Value error, ")
        message = msgs.t(raw) if msgs.has(raw) else msgs.validation_error
        return _error(422, ErrorCode.VALIDATION_422, message)

    @app.exception_handler(SQLAlchemyError)
    async def _db(request: Request, exc: SQLAlchemyError):
        logger.exception("database error")  # traceback only in logs, never in the response
        msgs = get_messages(resolve_language(request.headers.get("accept-language")))
        return _error(500, ErrorCode.SYSTEM_500, msgs.system_error)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        logger.exception("unhandled error")
        msgs = get_messages(resolve_language(request.headers.get("accept-language")))
        return _error(500, ErrorCode.SYSTEM_500, msgs.system_error)
