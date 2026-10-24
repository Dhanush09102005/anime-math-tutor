"""
ORM models. Mirrors the old sessions/attempts schema, adds users.

sessions.user_id is NOT NULL — every session belongs to exactly one user
now that auth is required to create one. There's no backward-compat path
for anonymous sessions; that's intentional (see CreateSessionRequest flow
in routes/session.py, which requires get_current_user).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=True)
    oauth_provider = Column(String, nullable=True)
    oauth_id = Column(String, nullable=True)
    display_name = Column(String, nullable=True)       # user-set display name
    avatar_url = Column(String, nullable=True)         # uploaded avatar, stored as URL/path
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    sessions = relationship(
        "SessionModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("oauth_provider", "oauth_id", name="uq_oauth_identity"),
    )


class SessionModel(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    persona_id = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    mode = Column(String, nullable=False, default="qna")   # "qna" | "chat"
    difficulty = Column(Integer, nullable=False)
    streak = Column(Integer, nullable=False, default=0)
    mastery_announced = Column(Boolean, nullable=False, default=False)
    last_mistake_type = Column(String, nullable=True)
    consecutive_wrong = Column(Integer, nullable=False, default=0)
    current_problem = Column(JSONB, nullable=True)
    conversation_history = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    user = relationship("User", back_populates="sessions")
    attempts = relationship(
        "Attempt",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"), nullable=False, index=True)
    problem_id = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    difficulty = Column(Integer, nullable=False)
    correct = Column(Boolean, nullable=False)
    mistake_type = Column(String, nullable=True)
    event_category = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    session = relationship("SessionModel", back_populates="attempts")
