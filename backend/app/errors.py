import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """An expected failure with a stable machine-readable `code`."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "payload_too_large"


class ReviewerFailedError(AppError):
    status_code = 502
    code = "reviewer_failed"


class NotReadyError(AppError):
    status_code = 503
    code = "not_ready"


def _response(
    request: Request, status: int, code: str, message: str, details: Any = None
) -> JSONResponse:
    """Every error uses one shape: {"error": {"code", "message", "requestId", "details"?}}."""
    request_id = getattr(request.state, "request_id", None)
    error: dict[str, Any] = {"code": code, "message": message, "requestId": request_id}
    if details is not None:
        error["details"] = details
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse({"error": error}, status_code=status, headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _response(request, exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
            for e in exc.errors()
        ]
        return _response(request, 422, "validation_error", "The request is not valid.", details)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "http_error"
        return _response(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=exc)
        return _response(request, 500, "internal_error", "Something went wrong on our side.")
