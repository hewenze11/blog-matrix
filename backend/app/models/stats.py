from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class BlogEvent(Base):
    __tablename__ = "blog_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    blog_id = Column(String(36), ForeignKey("blogs.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(30), nullable=False)  # pageview | click_apimart | click_other
    country = Column(String(10), nullable=True)
    device = Column(String(20), nullable=True)       # mobile | desktop
    referrer = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_blog_events_blog_id", "blog_id"),
        Index("ix_blog_events_created_at", "created_at"),
        Index("ix_blog_events_type", "event_type"),
    )
