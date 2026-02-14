"""
Pydantic models for Account management
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AccountBase(BaseModel):
    name: str = Field(..., min_length=1)
    sessdata: str = Field(..., min_length=1)
    bili_jct: str = Field(..., min_length=1)
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


class AccountPublic(BaseModel):
    """Account model excluding sensitive credential fields."""
    id: int
    name: str
    uid: Optional[int] = None
    buvid3: Optional[str] = ""
    buvid4: Optional[str] = ""
    group_tag: Optional[str] = "default"
    is_active: bool = True
    last_check_at: Optional[datetime] = None
    status: str = "unknown"
    created_at: datetime

    class Config:
        from_attributes = True


class AccountImport(BaseModel):
    """Validated model for account import."""
    name: str = Field(..., min_length=1)
    sessdata: str = Field(..., min_length=1)
    bili_jct: str = Field(..., min_length=1)
    buvid3: Optional[str] = ""
    buvid4: Optional[str] = ""
    dedeuserid_ckmd5: Optional[str] = ""
    group_tag: Optional[str] = "default"


class AccountStatus(BaseModel):
    id: int
    name: str = Field(..., min_length=1)
    status: str
    is_valid: bool
    uid: Optional[int] = None


class AccountCredentials(BaseModel):
    """Account credentials response (sensitive data)."""
    id: int
    name: str
    sessdata: str
    bili_jct: str
    buvid3: str
    buvid4: str
