"""
Pydantic models for Scheduled Tasks and Auto-Reply
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


TaskType = Literal["report_batch", "autoreply_poll", "cookie_health_check", "log_cleanup"]


class ScheduledTaskBase(BaseModel):
    name: str
    task_type: TaskType
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    config_json: Optional[dict] = None


class ScheduledTaskCreate(ScheduledTaskBase):
    pass


class ScheduledTaskUpdate(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    is_active: Optional[bool] = None
    config_json: Optional[dict] = None


class ScheduledTask(ScheduledTaskBase):
    id: int
    is_active: bool = True
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Auto-reply models
class AutoReplyConfigBase(BaseModel):
    keyword: Optional[str] = None  # None = default reply
    response: str = Field(..., min_length=1)
    priority: int = 0


class AutoReplyConfigCreate(AutoReplyConfigBase):
    pass


class AutoReplyConfigUpdate(BaseModel):
    keyword: Optional[str] = None
    response: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class AutoReplyConfig(AutoReplyConfigBase):
    id: int
    is_active: bool = True

    class Config:
        from_attributes = True


class AutoReplyStatus(BaseModel):
    is_running: bool
    active_accounts: int
    last_poll_at: Optional[datetime] = None
