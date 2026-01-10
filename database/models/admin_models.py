from sqlalchemy import Integer, String, DateTime, Boolean, func, JSON, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base
from datetime import datetime


class AdminLog(Base):
    __tablename__ = "admin_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String)
    target_id: Mapped[int | None] = mapped_column(BigInteger)
    details: Mapped[dict | None] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Broadcast(Base):
    __tablename__ = "broadcasts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_text: Mapped[str] = mapped_column(Text)
    photo_file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    video_file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    document_file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    scheduled_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    blocked_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer)


class ScheduledBroadcast(Base):
    __tablename__ = "scheduled_broadcasts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_text: Mapped[str] = mapped_column(Text)
    photo_file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    video_file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    document_file_id: Mapped[str | None] = mapped_column(String, nullable=True)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    created_by: Mapped[int] = mapped_column(Integer)