"""Request/Response schemas for Account endpoints."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ── Request schemas ───────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    name: str
    sessdata: str
    bili_jct: str
    buvid3: Optional[str] = ""
    group_tag: Optional[str] = "default"


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    sessdata: Optional[str] = None
    bili_jct: Optional[str] = None
    buvid3: Optional[str] = None
    group_tag: Optional[str] = None
    is_active: Optional[bool] = None


# ── Response schemas ──────────────────────────────────────────────────────

class AccountResponse(BaseModel):
    id: int
    name: str
    sessdata: str
    bili_jct: str
    buvid3: Optional[str] = ""
    group_tag: Optional[str] = "default"
    uid: Optional[int] = None
    is_active: bool = True
    last_check_at: Optional[datetime] = None
    status: str = "unknown"
    created_at: datetime

    class Config:
        from_attributes = True


class AccountStatusResponse(BaseModel):
    id: int
    name: str
    status: str
    is_valid: bool
    uid: Optional[int] = None
