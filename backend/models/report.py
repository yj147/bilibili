"""
Pydantic models for Report operations
"""
from pydantic import BaseModel, field_validator
from typing import Optional, Any
from datetime import datetime
import json


class ReportExecuteRequest(BaseModel):
    target_id: int
    account_ids: Optional[list[int]] = None  # None = use all active accounts


class ReportBatchExecuteRequest(BaseModel):
    target_ids: Optional[list[int]] = None  # None = all pending targets
    account_ids: Optional[list[int]] = None


class ReportLog(BaseModel):
    id: int
    target_id: int
    account_id: Optional[int]
    account_name: Optional[str] = None
    action: str
    request_data: Optional[dict] = None
    response_data: Optional[dict] = None
    success: bool
    error_message: Optional[str] = None
    executed_at: datetime

    @field_validator('request_data', 'response_data', mode='before')
    @classmethod
    def parse_json_string(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    class Config:
        from_attributes = True


class ReportResult(BaseModel):
    target_id: int
    account_id: int
    account_name: str
    success: bool
    message: str
    response: Optional[Any] = None


class BatchReportResult(BaseModel):
    total_targets: int
    total_accounts: int
    successful: int
    failed: int
    results: list[ReportResult]
