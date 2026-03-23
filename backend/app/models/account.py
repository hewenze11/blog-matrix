from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum
from sqlalchemy.sql import func
from app.core.database import Base
import uuid
import enum


class AccountStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    error = "error"


class CFAccount(Base):
    __tablename__ = "cf_accounts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    account_id = Column(String(100), nullable=False, unique=True)
    api_token = Column(String(200), nullable=False)
    status = Column(Enum(AccountStatus), default=AccountStatus.active)
    site_count = Column(String(10), default="0")
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
