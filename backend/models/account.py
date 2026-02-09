"""
Pydantic models for Account management
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AccountBase(BaseModel):
    name: str
    sessdata: str
    bili_jct: str
    buvid3: Optional[str] = ""
    buvid4: Optional[str] = ""
    dedeuserid_ckmd5: Optional[str] = ""
    refresh_token: Optional[str] = ""
    group_tag: Optional[str] = "default"


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    sessdata: Optional[str] = None
    bili_jct: Optional[str] = None
    buvid3: Optional[str] = None
    buvid4: Optional[str] = None
    dedeuserid_ckmd5: Optional[str] = None
    refresh_token: Optional[str] = None
    group_tag: Optional[str] = None
    is_active: Optional[bool] = None


class Account(AccountBase):
    id: int
    uid: Optional[int] = None
    is_active: bool = True
    last_check_at: Optional[datetime] = None
    status: str = "unknown"
    created_at: datetime

    class Config:
        from_attributes = True


class AccountStatus(BaseModel):
    id: int
    name: str
    status: str
    is_valid: bool
    uid: Optional[int] = None
