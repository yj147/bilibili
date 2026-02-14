"""
Pydantic models for Scheduled Tasks and Auto-Reply
"""
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, Literal
from datetime import datetime
from apscheduler.triggers.cron import CronTrigger


TaskType = Literal["report_batch", "autoreply_poll", "cookie_health_check", "log_cleanup"]

def _normalize_cron_expression(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class ScheduledTaskBase(BaseModel):
    name: str
    task_type: TaskType
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = Field(None, ge=10, le=2592000)
    config_json: Optional[dict] = None

    @field_validator('cron_expression')
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        v = _normalize_cron_expression(v)
        if v is not None:
            try:
                CronTrigger.from_crontab(v)
            except Exception as e:
                raise ValueError(f"Invalid cron expression: {v}") from e
        return v

    @model_validator(mode='after')
    def validate_scheduling(self):
        if self.cron_expression is None and self.interval_seconds is None:
            raise ValueError("Either cron_expression or interval_seconds must be set")
        if self.cron_expression is not None and self.interval_seconds is not None:
            raise ValueError("Cannot set both cron_expression and interval_seconds")
        return self


class ScheduledTaskCreate(ScheduledTaskBase):
    pass


class ScheduledTaskUpdate(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = Field(None, ge=10, le=2592000)
    is_active: Optional[bool] = None
    config_json: Optional[dict] = None

    @field_validator('cron_expression')
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        v = _normalize_cron_expression(v)
        if v is not None:
            try:
                CronTrigger.from_crontab(v)
            except Exception as e:
                raise ValueError(f"Invalid cron expression: {v}") from e
        return v

    @model_validator(mode='after')
    def validate_trigger_pair(self):
        has_cron = "cron_expression" in self.model_fields_set
        has_interval = "interval_seconds" in self.model_fields_set
        if has_cron and has_interval:
            if self.cron_expression is None and self.interval_seconds is None:
                raise ValueError("Either cron_expression or interval_seconds must be set")
            if self.cron_expression is not None and self.interval_seconds is not None:
                raise ValueError("Cannot set both cron_expression and interval_seconds")
        return self


class ScheduledTask(ScheduledTaskBase):
    id: int
    is_active: bool = True
    last_run_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


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


class AutoReplyDefaultUpsert(BaseModel):
    response: str = Field(..., min_length=1)


class AutoReplyConfig(BaseModel):
    id: int
    keyword: Optional[str]
    response: str
    priority: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AutoReplyStatus(BaseModel):
    is_running: bool
    active_accounts: int
    last_poll_at: Optional[datetime] = None
