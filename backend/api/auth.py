"""Authentication API Routes - QR login and cookie refresh."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.services import auth_service

router = APIRouter()


class QRPollRequest(BaseModel):
    qrcode_key: str
    account_name: Optional[str] = "QR_login"


@router.get("/qr/generate")
async def qr_generate():
    """Generate a QR code URL for Bilibili login."""
    result = await auth_service.qr_generate()
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.post("/qr/poll")
async def qr_poll(req: QRPollRequest):
    """Poll QR code scan status. Returns cookies on success."""
    return await auth_service.qr_poll(req.qrcode_key)


@router.post("/qr/login")
async def qr_login(req: QRPollRequest):
    """Poll QR code and auto-save account on success."""
    return await auth_service.qr_login_save(req.qrcode_key, req.account_name)


@router.get("/{account_id}/cookie-status")
async def cookie_status(account_id: int):
    """Check if an account's cookies need refreshing."""
    result = await auth_service.check_cookie_refresh_needed(account_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{account_id}/refresh")
async def refresh_cookies(account_id: int):
    """Refresh an account's cookies using stored refresh_token."""
    return await auth_service.refresh_account_cookies(account_id)
