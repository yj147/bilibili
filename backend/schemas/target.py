"""Request/Response schemas for Target endpoints."""
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

TargetType = Literal["video", "comment", "user"]
TargetStatus = Literal["pending", "processing", "completed", "failed"]


# ── Request schemas ───────────────────────────────────────────────────────

class TargetCreate(BaseModel):
    type: TargetType
    identifier: str
    aid: Optional[int] = None
    reason_id: Optional[int] = None
    reason_content_id: Optional[int] = None
    reason_text: Optional[str] = None


class TargetBatchCreate(BaseModel):
    type: TargetType
    identifiers: list[str]
    reason_id: Optional[int] = None
    reason_content_id: Optional[int] = None
    reason_text: Optional[str] = None


class TargetUpdate(BaseModel):
    reason_id: Optional[int] = None
    reason_content_id: Optional[int] = None
    reason_text: Optional[str] = None
    status: Optional[TargetStatus] = None


# ── Response schemas ──────────────────────────────────────────────────────

class TargetResponse(BaseModel):
    id: int
    type: TargetType
    identifier: str
    aid: Optional[int] = None
    reason_id: Optional[int] = None
    reason_content_id: Optional[int] = None
    reason_text: Optional[str] = None
    status: TargetStatus = "pending"
    retry_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TargetListResponse(BaseModel):
    items: list[TargetResponse]
    total: int
    page: int
    page_size: int
