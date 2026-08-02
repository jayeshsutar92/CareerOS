import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.agents.exceptions import AgentError, AgentValidationError
from app.ai.exceptions import AIConfigurationError, AIError

logger = logging.getLogger(__name__)


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details is not None:
        content["error"]["details"] = jsonable_encoder(details)

    return JSONResponse(status_code=status_code, content=content)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return error_response(
            status_code=exc.status_code,
            code="http_error",
            message=detail,
            details=None if isinstance(exc.detail, str) else exc.detail,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="validation_error",
            message="Request validation failed",
            details=exc.errors(),
        )

    @app.exception_handler(AIConfigurationError)
    async def ai_configuration_exception_handler(
        _request: Request,
        exc: AIConfigurationError,
    ) -> JSONResponse:
        return error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="ai_configuration_error",
            message=str(exc),
        )

    @app.exception_handler(AIError)
    async def ai_exception_handler(_request: Request, exc: AIError) -> JSONResponse:
        return error_response(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="ai_provider_error",
            message=str(exc) or "AI provider request failed",
        )

    @app.exception_handler(AgentValidationError)
    async def agent_validation_exception_handler(
        _request: Request,
        exc: AgentValidationError,
    ) -> JSONResponse:
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="agent_validation_error",
            message=str(exc),
        )

    @app.exception_handler(AgentError)
    async def agent_exception_handler(_request: Request, exc: AgentError) -> JSONResponse:
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="agent_error",
            message=str(exc) or "Agent execution failed",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled application exception",
            extra={"method": request.method, "path": request.url.path},
            exc_info=True,
        )
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="internal_server_error",
            message="Internal server error",
        )
