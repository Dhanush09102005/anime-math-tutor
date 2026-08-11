import uuid
from fastapi import APIRouter, HTTPException

import state
from schemas import CreateSessionRequest, CreateSessionResponse

router = APIRouter()


def get_session(session_id: str) -> dict:
    """Shared lookup used by the other route files too — see problem.py / submit.py imports."""
    session = state.SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session_id. Create one via POST /session.")
    return session


@router.post("/session", response_model=CreateSessionResponse)
def create_session(req: CreateSessionRequest):
    session_id = str(uuid.uuid4())
    state.SESSIONS[session_id] = state.new_session_state(req.persona_id)
    s = state.SESSIONS[session_id]
    return CreateSessionResponse(
        session_id=session_id,
        persona_id=s["persona_id"],
        topic=s["topic"],
        difficulty=s["difficulty"],
    )