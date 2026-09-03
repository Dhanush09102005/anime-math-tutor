"""
CRUD operations, ORM-backed.

Function names/shapes deliberately mirror the old db/database.py module
(create_session, load_session, update_session, log_attempt) so callers in
routes/ change minimally: add a `db: Session` param (from Depends(get_db))
and, for session ops, a `user_id`. See routes/session.py for the pattern —
routes/problem.py, routes/submit.py, routes/chat.py need the identical
treatment wherever they currently call the old db.* functions.
"""

import uuid
from typing import Optional

from sqlalchemy import func
from sqlalchemy import Integer, func
from sqlalchemy.orm import Session

from db.models import User, SessionModel, Attempt


# ── User operations ───────────────────────────────────────────────────────────

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_oauth(db: Session, provider: str, oauth_id: str) -> Optional[User]:
    return db.query(User).filter(
        User.oauth_provider == provider, User.oauth_id == oauth_id
    ).first()


def create_user(
    db: Session,
    email: str,
    hashed_password: Optional[str] = None,
    oauth_provider: Optional[str] = None,
    oauth_id: Optional[str] = None,
) -> User:
    user = User(
        email=email,
        hashed_password=hashed_password,
        oauth_provider=oauth_provider,
        oauth_id=oauth_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── Session operations ────────────────────────────────────────────────────────

def create_session(
    db: Session,
    session_id: str,
    user_id: uuid.UUID,
    persona_id: str,
    topic: str,
    difficulty: int,
) -> None:
    obj = SessionModel(
        session_id=session_id,
        user_id=user_id,
        persona_id=persona_id,
        topic=topic,
        difficulty=difficulty,
        streak=0,
        mastery_announced=False,
        last_mistake_type=None,
    )
    db.add(obj)
    db.commit()


def load_session(db: Session, session_id: str) -> Optional[dict]:
    """Returns session as a dict (including user_id, for ownership checks), or None."""
    row = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if row is None:
        return None
    return {
        "user_id":           row.user_id,
        "persona_id":        row.persona_id,
        "topic":             row.topic,
        "difficulty":        row.difficulty,
        "streak":            row.streak,
        "mastery_announced": row.mastery_announced,
        "last_mistake_type": row.last_mistake_type,
        "current_problem":   None,   # never persisted — always starts empty
    }


def update_session(
    db: Session,
    session_id: str,
    difficulty: int,
    streak: int,
    mastery_announced: bool,
    last_mistake_type: Optional[str],
    topic: str,
) -> None:
    db.query(SessionModel).filter(SessionModel.session_id == session_id).update({
        "difficulty": difficulty,
        "streak": streak,
        "mastery_announced": mastery_announced,
        "last_mistake_type": last_mistake_type,
        "topic": topic,
    })
    db.commit()


def list_sessions_for_user(db: Session, user_id: uuid.UUID) -> list[dict]:
    """Returns session summaries for one user, newest first."""
    rows = (
        db.query(
            SessionModel,
            func.count(Attempt.id).label("attempt_count"),
            func.coalesce(func.sum(Attempt.correct.cast(Integer)), 0).label("correct_count"),
        )
        .outerjoin(Attempt, Attempt.session_id == SessionModel.session_id)
        .filter(SessionModel.user_id == user_id)
        .group_by(SessionModel.session_id)
        .order_by(SessionModel.created_at.desc())
        .all()
    )

    return [
        {
            "session_id": session.session_id,
            "persona_id": session.persona_id,
            "topic": session.topic,
            "difficulty": session.difficulty,
            "streak": session.streak,
            "attempt_count": attempt_count,
            "correct_count": int(correct_count),
            "created_at": session.created_at.isoformat(),
        }
        for session, attempt_count, correct_count in rows
    ]


# ── Attempt logging ───────────────────────────────────────────────────────────

def log_attempt(
    db: Session,
    session_id: str,
    problem_id: str,
    topic: str,
    difficulty: int,
    correct: bool,
    mistake_type: Optional[str],
    event_category: str,
) -> None:
    obj = Attempt(
        session_id=session_id,
        problem_id=problem_id,
        topic=topic,
        difficulty=difficulty,
        correct=correct,
        mistake_type=mistake_type,
        event_category=event_category,
    )
    db.add(obj)
    db.commit()
