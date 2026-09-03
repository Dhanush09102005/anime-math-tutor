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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)

    # Null for OAuth-only accounts — a user who only ever signed in via
    # Google has no password to hash. verify checks for this before
    # attempting password comparison (see routes/auth.py login()).
    hashed_password = Column(String, nullable=True)

    oauth_provider = Column(String, nullable=True)  # e.g. "google"; null for password-only accounts
    oauth_id = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    sessions = relationship("SessionModel", back_populates="user")

    __table_args__ = (
        UniqueConstraint("oauth_provider", "oauth_id", name="uq_oauth_identity"),
    )


class SessionModel(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    persona_id = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    difficulty = Column(Integer, nullable=False)
    streak = Column(Integer, nullable=False, default=0)
    mastery_announced = Column(Boolean, nullable=False, default=False)
    last_mistake_type = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    user = relationship("User", back_populates="sessions")
    attempts = relationship("Attempt", back_populates="session")


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
