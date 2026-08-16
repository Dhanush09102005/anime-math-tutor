import uuid
from fastapi import APIRouter, HTTPException

import state
import db.database as db
from schemas import CreateSessionRequest, CreateSessionResponse

router = APIRouter()


def get_session(session_id: str) -> dict:
    """
    Returns the session dict for a given session_id.
    Checks in-memory cache first. If not found (e.g. after server restart),
    falls back to loading from the DB and repopulating the cache.
    """
    s = state.SESSIONS.get(session_id)
    if s is not None:
        return s

    # Memory miss — try DB (handles server restarts mid-session)
    s = db.load_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Unknown session_id. Create one via POST /session.")

    # Repopulate memory cache from DB row
    state.SESSIONS[session_id] = s
    return s


@router.post("/session", response_model=CreateSessionResponse)
def create_session(req: CreateSessionRequest):
    session_id = str(uuid.uuid4())
    s = state.new_session_state(req.persona_id)
    s["mode"] = req.mode
    if req.topic:
        s["topic"] = req.topic
    state.SESSIONS[session_id] = s

    # Persist to DB
    db.create_session(
        session_id=session_id,
        persona_id=s["persona_id"],
        topic=s["topic"],
        difficulty=s["difficulty"],
    )

    return CreateSessionResponse(
        session_id=session_id,
        persona_id=s["persona_id"],
        topic=s["topic"],
        difficulty=s["difficulty"],
        mode=s["mode"],
    )
