from sqlalchemy import Column, String, DateTime, Text, Enum, Integer, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base
import uuid
import enum


class TaskStatus(str, enum.Enum):
    pending = "pending"      # 排队等待
    running = "running"      # 编译中
    success = "success"      # 成功
    failed = "failed"        # 失败


class BuildTask(Base):
    __tablename__ = "build_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    blog_id = Column(String(36), ForeignKey("blogs.id", ondelete="CASCADE"), nullable=False)
    blog_name = Column(String(200), nullable=False)
    theme = Column(String(50), nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.pending, nullable=False)
    queue_position = Column(Integer, default=0)   # 排队位置（0=正在运行）
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    log = Column(Text, default="等待队列调度...")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
