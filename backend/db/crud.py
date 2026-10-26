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

from sqlalchemy import Integer, func
from sqlalchemy.orm import Session

from db.models import User, SessionModel, Attempt
from db.session_state import deserialize_active_problem, serialize_active_problem, serialize_conversation_history


# ── User operations ───────────────────────────────────────────────────────────

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_oauth(db: Session, provider: str, oauth_id: str) -> Optional[User]:
    return db.query(User).filter(
        User.oauth_provider == provider, User.oauth_id == oauth_id
    ).first()


def link_user_oauth(db: Session, user: User, provider: str, oauth_id: str) -> User:
    user.oauth_provider = provider
    user.oauth_id = oauth_id
    db.commit()
    db.refresh(user)
    return user


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
    mode: str = "qna",
) -> None:
    obj = SessionModel(
        session_id=session_id,
        user_id=user_id,
        persona_id=persona_id,
        topic=topic,
        mode=mode,
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
        "mode":              row.mode if hasattr(row, "mode") else "qna",
        "difficulty":        row.difficulty,
        "streak":            row.streak,
        "mastery_announced": row.mastery_announced,
        "last_mistake_type": row.last_mistake_type,
        "current_problem": deserialize_active_problem(row.current_problem),
        "conversation_history": row.conversation_history or [],
        "consecutive_wrong": row.consecutive_wrong,
    }


def update_session(
    db: Session,
    session_id: str,
    difficulty: int,
    streak: int,
    mastery_announced: bool,
    last_mistake_type: Optional[str],
    topic: str,
    current_problem: Optional[dict],
    conversation_history: list[dict],
    consecutive_wrong: int,
) -> None:
    db.query(SessionModel).filter(SessionModel.session_id == session_id).update({
        "difficulty": difficulty,
        "streak": streak,
        "mastery_announced": mastery_announced,
        "last_mistake_type": last_mistake_type,
        "topic": topic,
        "current_problem": serialize_active_problem(current_problem),
        "conversation_history": serialize_conversation_history(conversation_history),
        "consecutive_wrong": consecutive_wrong,
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
            "mode": session.mode,
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

def get_attempts_for_session(db: Session, session_id: str) -> list[dict]:
    """Returns all attempts for a session, oldest first."""
    rows = (
        db.query(Attempt)
        .filter(Attempt.session_id == session_id)
        .order_by(Attempt.timestamp.asc())
        .all()
    )
    return [
        {
            "id": row.id,
            "problem_id": row.problem_id,
            "topic": row.topic,
            "difficulty": row.difficulty,
            "correct": row.correct,
            "mistake_type": row.mistake_type,
            "event_category": row.event_category,
            "timestamp": row.timestamp.isoformat(),
        }
        for row in rows
    ]


def update_user_password(db: Session, user_id: uuid.UUID, hashed_password: str) -> None:
    db.query(User).filter(User.id == user_id).update({"hashed_password": hashed_password})
    db.commit()


def delete_user(db: Session, user_id: uuid.UUID) -> None:
    """
    Deletes user and all their data in dependency order.
    Belt-and-suspenders: explicit deletes before removing the user row,
    even though the ORM cascade="all, delete-orphan" on the relationships
    should handle it — some Postgres FK configurations require explicit
    ordering when using .delete() rather than session.delete(obj).
    """
    # Get all session IDs for this user first
    session_ids = [
        row.session_id
        for row in db.query(SessionModel.session_id)
        .filter(SessionModel.user_id == user_id)
        .all()
    ]
    if session_ids:
        db.query(Attempt).filter(Attempt.session_id.in_(session_ids)).delete(synchronize_session=False)
    db.query(SessionModel).filter(SessionModel.user_id == user_id).delete(synchronize_session=False)
    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
    db.commit()

def get_analytics(db: Session, user_id: uuid.UUID) -> dict:
    """
    Aggregates attempt data per topic for the given user.
    Returns per-topic accuracy, attempt counts, best difficulty reached,
    and overall totals.
    """
    rows = (
        db.query(
            Attempt.topic,
            func.count(Attempt.id).label("total"),
            func.coalesce(func.sum(Attempt.correct.cast(Integer)), 0).label("correct"),
            func.max(Attempt.difficulty).label("best_difficulty"),
        )
        .join(SessionModel, SessionModel.session_id == Attempt.session_id)
        .filter(SessionModel.user_id == user_id)
        .group_by(Attempt.topic)
        .all()
    )

    topics = []
    total_attempts = 0
    total_correct = 0

    for topic, total, correct, best_difficulty in rows:
        total_attempts += total
        total_correct += int(correct)
        topics.append({
            "topic": topic,
            "total_attempts": total,
            "correct_attempts": int(correct),
            "accuracy": round(int(correct) / total * 100) if total else 0,
            "best_difficulty": best_difficulty or 1,
        })

    # Sort by most attempted first
    topics.sort(key=lambda t: t["total_attempts"], reverse=True)

    return {
        "total_attempts": total_attempts,
        "total_correct": total_correct,
        "overall_accuracy": round(total_correct / total_attempts * 100) if total_attempts else 0,
        "topics": topics,
    }


def get_syllabus_progress(db: Session, user_id: uuid.UUID) -> dict:
    """
    Returns mastery status per topic based on whether the user has
    ever reached difficulty >= MASTERY_THRESHOLD on that topic.
    """
    MASTERY_THRESHOLD = 8

    rows = (
        db.query(
            Attempt.topic,
            func.count(Attempt.id).label("total"),
            func.coalesce(func.sum(Attempt.correct.cast(Integer)), 0).label("correct"),
            func.max(Attempt.difficulty).label("best_difficulty"),
        )
        .join(SessionModel, SessionModel.session_id == Attempt.session_id)
        .filter(SessionModel.user_id == user_id)
        .group_by(Attempt.topic)
        .all()
    )

    progress = {}
    for topic, total, correct, best_difficulty in rows:
        accuracy = round(int(correct) / total * 100) if total else 0
        mastered = (best_difficulty or 0) >= MASTERY_THRESHOLD
        started  = total > 0
        progress[topic] = {
            "started": started,
            "mastered": mastered,
            "accuracy": accuracy,
            "best_difficulty": best_difficulty or 0,
            "total_attempts": total,
        }

    return progress

def update_user_profile(db: Session, user_id: uuid.UUID,
                        display_name: str | None = None,
                        avatar_url: str | None = None) -> None:
    updates = {}
    if display_name is not None:
        updates["display_name"] = display_name
    if avatar_url is not None:
        updates["avatar_url"] = avatar_url
    if updates:
        db.query(User).filter(User.id == user_id).update(updates)
        db.commit()
