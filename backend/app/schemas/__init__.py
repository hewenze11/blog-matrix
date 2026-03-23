from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.account import AccountStatus
from app.models.blog import BlogStatus, ThemeType


# ── Auth ──────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ── CF Account ─────────────────────────────────────────────────────────────
class CFAccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    account_id: str = Field(..., min_length=10)
    api_token: str = Field(..., min_length=10)

class CFAccountOut(BaseModel):
    id: str
    name: str
    account_id: str
    status: AccountStatus
    site_count: str
    last_verified_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Blog ───────────────────────────────────────────────────────────────────
class BlogCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    custom_domain: str = Field(..., description="主域名，如 myblog.com")
    cf_account_id: str = Field(..., description="CF账号ID（平台内部ID）")
    theme: ThemeType = ThemeType.minimal_white
    content_markdown: Optional[str] = Field(None, description="博客首页Markdown内容")

class BlogOut(BaseModel):
    id: str
    name: str
    slug: str
    custom_domain: Optional[str]
    pages_domain: Optional[str]
    cf_project_name: Optional[str]
    cf_account_id: str
    theme: ThemeType
    status: BlogStatus
    fail_count: int
    last_deployed_at: Optional[datetime]
    last_checked_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class CNAMEBindRequest(BaseModel):
    blog_id: str
    confirmed: bool = True


# ── Monitor ────────────────────────────────────────────────────────────────
class MonitorStatus(BaseModel):
    blog_id: str
    blog_name: str
    url: str
    status_code: Optional[int]
    is_online: bool
    checked_at: datetime
