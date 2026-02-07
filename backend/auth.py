"""
Bili-Sentinel API Key Authentication
"""
import os
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader

_API_KEY = os.getenv("SENTINEL_API_KEY", "")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Routes that skip authentication
_PUBLIC_PATHS = {"/", "/health", "/docs", "/redoc", "/openapi.json"}


async def verify_api_key(request: Request, api_key: str | None = Security(_api_key_header)):
    """Global dependency: verify API key if SENTINEL_API_KEY is set."""
    if not _API_KEY:
        return  # auth disabled
    if request.url.path in _PUBLIC_PATHS:
        return  # public route
    if api_key and api_key == _API_KEY:
        return
    raise HTTPException(status_code=401, detail="Invalid or missing API key")
