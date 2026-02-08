"""Request/Response schemas for Scheduler and Auto-Reply endpoints."""
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

TaskType = Literal["report_batch", "autoreply_poll"]


# ── Scheduler Request schemas ─────────────────────────────────────────────

class ScheduledTaskCreate(BaseModel):
    name: str
    task_type: TaskType
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    config_json: Optional[dict] = None


class ScheduledTaskUpdate(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    is_active: Optional[bool] = None
    config_json: Optional[dict] = None


# ── Scheduler Response schemas ────────────────────────────────────────────

class ScheduledTaskResponse(BaseModel):
    id: int
    name: str
    task_type: TaskType
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    config_json: Optional[dict] = None
    is_active: bool = True
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Auto-Reply Request schemas ────────────────────────────────────────────

class AutoReplyConfigCreate(BaseModel):
    keyword: Optional[str] = None
    response: str
    priority: int = 0


class AutoReplyConfigUpdate(BaseModel):
    keyword: Optional[str] = None
    response: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


# ── Auto-Reply Response schemas ───────────────────────────────────────────

class AutoReplyConfigResponse(BaseModel):
    id: int
    keyword: Optional[str] = None
    response: str
    priority: int = 0
    is_active: bool = True

    class Config:
        from_attributes = True


class AutoReplyStatusResponse(BaseModel):
    is_running: bool
    active_accounts: int
    last_poll_at: Optional[datetime] = None
