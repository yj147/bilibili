"""
Pydantic models for Target management
"""
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


TargetType = Literal["video", "comment", "user"]
TargetStatus = Literal["pending", "processing", "completed", "failed"]


class TargetBase(BaseModel):
    type: TargetType
    identifier: str  # BV号 / rpid / uid
    aid: Optional[int] = None
    reason_id: Optional[int] = None
    reason_content_id: Optional[int] = None
    reason_text: Optional[str] = None


class TargetCreate(TargetBase):
    pass


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


class Target(TargetBase):
    id: int
    status: TargetStatus = "pending"
    retry_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TargetListResponse(BaseModel):
    items: list[Target]
    total: int
    page: int
    page_size: int
