"""
Bili-Sentinel API Key Authentication
"""
import hmac
import os
from fastapi import HTTPException, Request

_API_KEY = os.getenv("SENTINEL_API_KEY", "")

# Routes that skip authentication
_PUBLIC_PATHS = {"/", "/health", "/docs", "/redoc", "/openapi.json"}


async def verify_api_key(request: Request):
    """Global dependency: verify API key if SENTINEL_API_KEY is set.

    WebSocket routes handle their own auth via query params, so skip them here.
    """
    # WebSocket connections are handled by their own auth logic
    if request.scope.get("type") == "websocket":
        return
    if not _API_KEY:
        return  # auth disabled
    if request.url.path in _PUBLIC_PATHS:
        return  # public route
    api_key = request.headers.get("x-api-key")
    if api_key and hmac.compare_digest(api_key, _API_KEY):
        return
    raise HTTPException(status_code=401, detail="Invalid or missing API key")
