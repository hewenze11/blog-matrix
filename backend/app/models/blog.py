from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum, Integer, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
import uuid
import enum


class BlogStatus(str, enum.Enum):
    building = "building"
    deploying = "deploying"
    online = "online"
    offline = "offline"
    error = "error"


class ThemeType(str, enum.Enum):
    minimal_white = "minimal-white"
    dark_tech = "dark-tech"
    magazine = "magazine"
    personal = "personal"
    enterprise = "enterprise"


class Blog(Base):
    __tablename__ = "blogs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False, unique=True)
    custom_domain = Column(String(200), nullable=True)
    pages_domain = Column(String(300), nullable=True)      # xxx.pages.dev
    cf_project_name = Column(String(200), nullable=True)
    cf_account_id = Column(String(36), ForeignKey("cf_accounts.id"), nullable=False)
    theme = Column(Enum(ThemeType), nullable=False)
    status = Column(Enum(BlogStatus), default=BlogStatus.building)
    fail_count = Column(Integer, default=0)
    last_deployed_at = Column(DateTime(timezone=True), nullable=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    build_log = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
