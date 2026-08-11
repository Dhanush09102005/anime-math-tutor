from fastapi import APIRouter

from math_engine.generate import generate_problem
from routes.session import get_session
import db.database as db
from schemas import ProblemRequest, ProblemResponse

router = APIRouter()


@router.post("/problem", response_model=ProblemResponse)
def get_problem(req: ProblemRequest):
    s = get_session(req.session_id)

    if req.topic:
        s["topic"] = req.topic
        # Persist the topic change so it survives a restart
        db.update_session(
            session_id=req.session_id,
            difficulty=s["difficulty"],
            streak=s["streak"],
            mastery_announced=s["mastery_announced"],
            last_mistake_type=s["last_mistake_type"],
            topic=s["topic"],
        )

    problem = generate_problem(s["topic"], s["difficulty"])
    s["current_problem"] = problem  # canonical_answer/equation stay server-side only

    return ProblemResponse(
        problem_id=problem["id"],
        topic=problem["topic"],
        difficulty=problem["difficulty"],
        prompt_text=problem["prompt_text"],
    )
