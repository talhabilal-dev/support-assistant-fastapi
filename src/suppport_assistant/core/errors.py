import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("suppport_assistant")


class AppError(Exception):
    """Base class for expected, handled application errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "ApplicationError"
    detail: str = "Application error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NotFound"
    detail = "Resource not found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "Conflict"
    detail = "Resource already exists"


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "AuthenticationError"
    detail = "Authentication failed"


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "PermissionDenied"
    detail = "You do not have permission to perform this action"


class ServiceUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "ServiceUnavailable"
    detail = "Service is temporarily unavailable"


def _error_response(
    status_code: int,
    detail: str,
    code: str,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    payload: dict[str, Any] = {"error": {"code": code, "detail": detail}}
    if errors is not None:
        payload["error"]["errors"] = errors
    return JSONResponse(status_code=status_code, content=payload)


async def _handle_rate_limit(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    return _error_response(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "Rate limit exceeded. Please try again later.",
        "RateLimitExceeded",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global handlers so every error leaves the API as structured JSON."""

    app.add_exception_handler(RateLimitExceeded, _handle_rate_limit)  # type: ignore[arg-type]

    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.detail, exc.code)

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(
        _: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return _error_response(exc.status_code, str(exc.detail), "HTTPException")

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
            for err in exc.errors()
        ]
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Validation failed",
            "ValidationError",
            errors=errors,
        )

    @app.exception_handler(Exception)
    async def _handle_uncaught_exception(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "Unhandled exception on %s %s", request.method, request.url.path
        )
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "An unexpected error occurred. Please try again later.",
            "InternalServerError",
        )
