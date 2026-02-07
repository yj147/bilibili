"""
Bili-Sentinel Unified Error Handling Middleware
"""
import traceback
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.logger import logger


def register_exception_handlers(app: FastAPI):
    """Register unified exception handlers on the FastAPI app."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": True, "code": exc.status_code, "detail": str(exc.detail)},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details = []
        for err in exc.errors():
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            details.append(f"{loc}: {err.get('msg', '')}")
        return JSONResponse(
            status_code=422,
            content={"error": True, "code": 422, "detail": "; ".join(details)},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
        logger.debug(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": True, "code": 500, "detail": "Internal server error"},
        )
