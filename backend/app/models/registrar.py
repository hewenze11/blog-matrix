from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum, Integer, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
import uuid
import enum

class RegistrarProvider(str, enum.Enum):
    tencent = "tencent"
    aliyun = "aliyun"

class RegistrarStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    error = "error"

class RegistrarAccount(Base):
    __tablename__ = "registrar_accounts"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    provider = Column(Enum(RegistrarProvider), nullable=False)
    secret_id = Column(Text, nullable=False)
    secret_key = Column(Text, nullable=False)
    status = Column(Enum(RegistrarStatus), default=RegistrarStatus.active)
    domain_count = Column(Integer, default=0)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class DomainStatus(str, enum.Enum):
    pending_registration = "pending_registration"
    registering = "registering"
    registered = "registered"
    dns_configuring = "dns_configuring"
    dns_configured = "dns_configured"
    cf_binding = "cf_binding"
    active = "active"
    error = "error"

class Domain(Base):
    __tablename__ = "domains"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    domain_name = Column(String(200), nullable=False, unique=True)
    registrar_account_id = Column(String(36), ForeignKey("registrar_accounts.id"), nullable=False)
    blog_id = Column(String(36), ForeignKey("blogs.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(DomainStatus), default=DomainStatus.pending_registration)
    cf_pages_target = Column(String(300), nullable=True)
    registrar_order_id = Column(String(200), nullable=True)
    expire_at = Column(DateTime(timezone=True), nullable=True)
    error_msg = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
