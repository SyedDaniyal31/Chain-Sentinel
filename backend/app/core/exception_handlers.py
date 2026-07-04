"""Global FastAPI exception handlers for production-grade error responses."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, OperationalError, ProgrammingError

from app.core.config import Settings
from app.core.exceptions import UnsupportedChainError
from app.schemas.errors import ErrorResponse

logger = logging.getLogger(__name__)


def _error_response(
    *,
    status_code: int,
    detail: str,
    error_code: str,
) -> JSONResponse:
    body = ErrorResponse(detail=detail, error_code=error_code)
    return JSONResponse(status_code=status_code, content=body.model_dump())


def register_exception_handlers(app: FastAPI, settings: Settings) -> None:
    """Attach structured JSON handlers for validation, database, and unhandled errors."""

    @app.exception_handler(UnsupportedChainError)
    async def unsupported_chain_handler(
        _request: Request,
        exc: UnsupportedChainError,
    ) -> JSONResponse:
        logger.info("Unsupported chain requested: %s", exc.chain_id)
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
            error_code="unsupported_chain",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        messages: list[str] = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error.get("loc", []) if part != "body")
            msg = str(error.get("msg", "Invalid value"))
            if location:
                messages.append(f"{location}: {msg}")
            else:
                messages.append(msg)

        detail = "; ".join(messages) if messages else "Request validation failed"
        logger.info("Request validation failed: %s", detail)
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="validation_error",
        )

    @app.exception_handler(ProgrammingError)
    async def programming_error_handler(
        _request: Request,
        exc: ProgrammingError,
    ) -> JSONResponse:
        logger.exception("Database programming error")
        detail = (
            "Database schema is incompatible with the application. "
            "Run `alembic upgrade head` and restart the API."
        )
        if settings.app_debug:
            detail = f"{detail} ({exc.orig})"
        return _error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="database_schema_error",
        )

    @app.exception_handler(OperationalError)
    async def operational_error_handler(
        _request: Request,
        exc: OperationalError,
    ) -> JSONResponse:
        logger.exception("Database operational error")
        detail = "Database is temporarily unavailable. Retry the request shortly."
        if settings.app_debug:
            detail = f"{detail} ({exc.orig})"
        return _error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="database_unavailable",
        )

    @app.exception_handler(DBAPIError)
    async def dbapi_error_handler(
        _request: Request,
        exc: DBAPIError,
    ) -> JSONResponse:
        logger.exception("Database error")
        detail = "A database error occurred while processing the request."
        if settings.app_debug:
            detail = f"{detail} ({exc.orig})"
        return _error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="database_error",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled exception")
        detail = "An unexpected server error occurred."
        if settings.app_debug:
            detail = f"{detail} ({type(exc).__name__}: {exc})"
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="internal_error",
        )
