"""
SQLAlchemy ORM models.
Tables are created automatically on startup via create_all().
"""
from datetime import datetime, date
from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime,
    ForeignKey, Integer, String, Text, Time, func,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)          # Telegram user_id
    username = Column(String(64), nullable=True)
    first_name = Column(String(64), nullable=True)

    # Conversation state machine
    state = Column(String(32), default="IDLE", nullable=False)
    current_step = Column(Integer, default=0, nullable=False)  # 1-3 for checkin

    # Temporary storage for in-progress checkin answers
    temp_challenge = Column(Text, nullable=True)
    temp_gratitude = Column(Text, nullable=True)

    # Streak
    streak_count = Column(Integer, default=0, nullable=False)
    last_checkin_date = Column(Date, nullable=True)

    # Reminder settings
    timezone = Column(String(64), nullable=True)
    reminder_time = Column(Time, nullable=True)
    reminders_enabled = Column(Boolean, default=True, nullable=False)

    # LLM toggle — can disable per user if needed
    llm_enabled = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(),
                        onupdate=func.now(), nullable=False)

    checkins = relationship("Checkin", back_populates="user", cascade="all, delete-orphan")
    reminder_logs = relationship("ReminderLog", back_populates="user", cascade="all, delete-orphan")
    magic_links = relationship("MagicLink", back_populates="user", cascade="all, delete-orphan")


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    challenge = Column(Text, nullable=False)
    gratitude = Column(Text, nullable=False)
    intention = Column(Text, nullable=False)

    # LLM response stored for audit
    llm_response = Column(Text, nullable=True)

    streak_at_time = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="checkins")


class ReminderLog(Base):
    __tablename__ = "reminder_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    message_sent = Column(Text, nullable=True)   # The actual text that was sent
    status = Column(String(16), default="sent")  # sent | failed | skipped
    sent_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="reminder_logs")


class MagicLink(Base):
    __tablename__ = "magic_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(64), nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="magic_links")
