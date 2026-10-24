import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

import state
from db.database import get_db
from db import crud
from db.models import User
from auth.dependencies import get_current_user
from schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    ProblemResponse,
    SessionHistoryItem,
    SessionResumeResponse,
)

router = APIRouter()


@router.get("/sessions", response_model=list[SessionHistoryItem])
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.list_sessions_for_user(db, current_user.id)


@router.get("/sessions/{session_id}/resume", response_model=SessionResumeResponse)
def resume_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = get_session(session_id, current_user, db)
    active_problem = session.get("current_problem")
    problem_response = None
    if active_problem is not None:
        problem_response = ProblemResponse(
            problem_id=active_problem["id"],
            topic=active_problem["topic"],
            difficulty=active_problem["difficulty"],
            prompt_text=active_problem["prompt_text"],
            answer_shape=active_problem["answer_shape"],
            generation_mode=active_problem.get("generation_mode", "procedural"),
        )

    return SessionResumeResponse(
        session_id=session_id,
        persona_id=session["persona_id"],
        mode=session["mode"],
        topic=session["topic"],
        difficulty=session["difficulty"],
        streak=session["streak"],
        active_problem=problem_response,
        conversation_history=(
            session["conversation_history"] if session["mode"] == "chat" else []
        ),
    )


def get_session(session_id: str, current_user: User, db: Session) -> dict:
    """
    Returns the session dict for a given session_id, scoped to current_user.

    Checks in-memory cache first. If not found (e.g. after server restart),
    falls back to loading from the DB and repopulating the cache.

    Callers in routes/problem.py, routes/submit.py, routes/chat.py all need
    the same signature change: add `current_user: User = Depends(get_current_user)`
    and `db: Session = Depends(get_db)` to the route, and pass both through
    to this function instead of the old single-arg get_session(session_id).
    """
    s = state.SESSIONS.get(session_id)
    if s is not None:
        _check_ownership(s, current_user)
        return s

    # Memory miss — try DB (handles server restarts mid-session)
    s = crud.load_session(db, session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Unknown session_id. Create one via POST /session.")
    _check_ownership(s, current_user)

    # Repopulate memory cache from DB row
    state.SESSIONS[session_id] = s
    return s


def _check_ownership(session: dict, current_user: User) -> None:
    if session["user_id"] != current_user.id:
        # 403 rather than 404 — a legitimate owner debugging a stale/wrong
        # session_id should be able to tell "not mine" apart from "doesn't
        # exist," while an unauthenticated guesser gets no extra signal
        # either way since they'd never reach a valid current_user at all.
        raise HTTPException(status_code=403, detail="This session belongs to another user.")


@router.post("/session", response_model=CreateSessionResponse)
def create_session(
    req: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session_id = str(uuid.uuid4())
    s = state.new_session_state(req.persona_id)
    s["mode"] = req.mode
    s["user_id"] = current_user.id
    if req.topic:
        s["topic"] = req.topic
    state.SESSIONS[session_id] = s

    # Persist to DB
    crud.create_session(
        db,
        session_id=session_id,
        user_id=current_user.id,
        persona_id=s["persona_id"],
        topic=s["topic"],
        difficulty=s["difficulty"],
        mode=s["mode"],
    )

    return CreateSessionResponse(
        session_id=session_id,
        persona_id=s["persona_id"],
        topic=s["topic"],
        difficulty=s["difficulty"],
        mode=s["mode"],
    )

@router.get("/sessions/{session_id}/attempts", response_model=list)
def get_session_attempts(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Ownership check — reuse get_session which already enforces it
    get_session(session_id, current_user, db)
    return crud.get_attempts_for_session(db, session_id)
