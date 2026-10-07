"""AppException / ErrorCode and the global handlers (blueprint ch. 5.6)."""

from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
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
    METHOD_NOT_ALLOWED_405 = "METHOD_NOT_ALLOWED_405"
    CONFLICT_409 = "CONFLICT_409"
    PAYLOAD_TOO_LARGE_413 = "PAYLOAD_TOO_LARGE_413"
    BUSINESS_422_EMAIL_EXISTS = "BUSINESS_422_EMAIL_EXISTS"
    VALIDATION_422 = "VALIDATION_422"
    RATE_LIMITED_429 = "RATE_LIMITED_429"
    SYSTEM_500 = "SYSTEM_500"
    SERVICE_UNAVAILABLE_503 = "SERVICE_UNAVAILABLE_503"


class AppException(Exception):
    """Raise from services. `message` is already localized (use self.message.<key>)."""

    def __init__(self, status_code: int, code: ErrorCode, message: str, data=None, headers: dict | None = None):
        super().__init__(message)
        self.status_code, self.code, self.message, self.data, self.headers = status_code, code, message, data, headers


def _error(
    request: Request, status_code: int, code: ErrorCode, message: str, data=None, headers: dict | None = None
) -> JSONResponse:
    body = ApiResponse[Any](status="0", status_code=status_code, code=code, message=message, data=data)
    payload = body.model_dump(by_alias=True, mode="json")
    request_id = getattr(request.state, "request_id", None)
    payload["requestId"] = request_id  # lets support trace the failing request in the logs
    out_headers = dict(headers or {})
    if request_id:
        # Unhandled 500s are answered outside the request-id middleware, so set the header here too.
        out_headers["X-Request-ID"] = request_id
    return JSONResponse(payload, status_code=status_code, headers=out_headers)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def _app(request: Request, exc: AppException):
        return _error(request, exc.status_code, exc.code, exc.message, exc.data, exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        msgs = get_messages(resolve_language(request.headers.get("accept-language")))
        known = {
            401: (ErrorCode.AUTH_401_UNAUTHORIZED, msgs.unauthorized),
            403: (ErrorCode.FORBIDDEN_403, msgs.forbidden),
            404: (ErrorCode.NOT_FOUND_404, msgs.not_found),
            405: (ErrorCode.METHOD_NOT_ALLOWED_405, msgs.method_not_allowed),
            413: (ErrorCode.PAYLOAD_TOO_LARGE_413, msgs.payload_too_large),
            429: (ErrorCode.RATE_LIMITED_429, msgs.too_many_requests),
            503: (ErrorCode.SERVICE_UNAVAILABLE_503, msgs.service_unavailable),
        }
        code, message = known.get(exc.status_code, (ErrorCode.BAD_REQUEST_400, msgs.bad_request))
        # Keep headers the framework or a rate limiter set (Allow, Retry-After, WWW-Authenticate).
        return _error(request, exc.status_code, code, message, headers=dict(exc.headers) if exc.headers else None)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        msgs = get_messages(resolve_language(request.headers.get("accept-language")))
        # Validators raise ValueError("<message_key>"); resolve the first one, else a generic message.
        raw = str(exc.errors()[0].get("msg", "")).removeprefix("Value error, ")
        message = msgs.t(raw) if msgs.has(raw) else msgs.validation_error
        return _error(request, 422, ErrorCode.VALIDATION_422, message)

    @app.exception_handler(IntegrityError)
    async def _integrity(request: Request, exc: IntegrityError):
        # Unique/FK violation that slipped past the service check (e.g. a race). Roll back is done by the
        # session dependency; never echo the SQL or constraint name to the client.
        logger.warning("integrity error: %s", exc.orig)
        msgs = get_messages(resolve_language(request.headers.get("accept-language")))
        return _error(request, 409, ErrorCode.CONFLICT_409, msgs.conflict)

    @app.exception_handler(SQLAlchemyError)
    async def _db(request: Request, exc: SQLAlchemyError):
        logger.exception("database error")  # traceback only in logs, never in the response
        msgs = get_messages(resolve_language(request.headers.get("accept-language")))
        return _error(request, 500, ErrorCode.SYSTEM_500, msgs.system_error)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        logger.exception("unhandled error")
        msgs = get_messages(resolve_language(request.headers.get("accept-language")))
        return _error(request, 500, ErrorCode.SYSTEM_500, msgs.system_error)
