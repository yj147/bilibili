"""
Pydantic models for Target management
"""
from pydantic import BaseModel, field_validator
from typing import Optional, Literal
from datetime import datetime


TargetType = Literal["video", "comment", "user"]
TargetStatus = Literal["pending", "processing", "completed", "failed"]

# Valid reason_id values for comment reports (B站评论举报API限制)
VALID_COMMENT_REASONS = {1, 2, 3, 4, 5, 7, 8, 9}


class TargetBase(BaseModel):
    type: TargetType
    identifier: str  # BV号 / rpid / uid
    aid: Optional[int] = None
    reason_id: Optional[int] = None
    reason_content_id: Optional[int] = None
    reason_text: Optional[str] = None
    display_text: Optional[str] = None


class TargetCreate(TargetBase):
    @field_validator('reason_id')
    @classmethod
    def validate_comment_reason(cls, v, info):
        """Validate reason_id for comment type targets."""
        if info.data.get('type') == 'comment' and v is not None:
            if v not in VALID_COMMENT_REASONS:
                raise ValueError(
                    f'Invalid reason_id for comment: {v}. '
                    f'Must be one of {sorted(VALID_COMMENT_REASONS)}'
                )
        return v

    @field_validator('identifier')
    @classmethod
    def validate_identifier_format(cls, v, info):
        """Validate identifier format based on target type."""
        target_type = info.data.get('type')
        if target_type:
            _validate_identifier(v, target_type)
        return v


def _validate_identifier(v: str, target_type: str) -> str:
    """Shared identifier format validation for single and batch creation."""
    if target_type == 'video':
        if not v.startswith('BV') and not v.isdigit():
            raise ValueError('Video identifier must be a BV number (e.g. BV1xx...) or numeric aid')
    elif target_type == 'comment':
        if ':' in v:
            parts = v.split(':')
            if len(parts) != 2:
                raise ValueError('Comment identifier with ":" must be "oid:rpid" format')
            try:
                int(parts[0])
                int(parts[1])
            except ValueError:
                raise ValueError('Comment identifier oid and rpid must be integers')
        else:
            try:
                int(v)
            except ValueError:
                raise ValueError('Comment identifier must be integer rpid or "oid:rpid" format')
    elif target_type == 'user':
        try:
            int(v)
        except ValueError:
            raise ValueError('User identifier must be a numeric uid')
    return v


class TargetBatchCreate(BaseModel):
    type: TargetType
    identifiers: list[str]
    reason_id: Optional[int] = None
    reason_content_id: Optional[int] = None
    reason_text: Optional[str] = None

    @field_validator('identifiers')
    @classmethod
    def validate_identifiers_format(cls, v, info):
        """Validate each identifier format based on target type."""
        target_type = info.data.get('type')
        if target_type:
            for identifier in v:
                _validate_identifier(identifier, target_type)
        return v


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
