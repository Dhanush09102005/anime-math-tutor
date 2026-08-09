from fastapi import APIRouter

from math_engine.generate import generate_problem
from routes.session import get_session
from schemas import ProblemRequest, ProblemResponse

router = APIRouter()


@router.post("/problem", response_model=ProblemResponse)
def get_problem(req: ProblemRequest):
    s = get_session(req.session_id)

    if req.topic:
        s["topic"] = req.topic

    problem = generate_problem(s["topic"], s["difficulty"])
    s["current_problem"] = problem  # canonical_answer/equation stay server-side only

    return ProblemResponse(
        problem_id=problem["id"],
        topic=problem["topic"],
        difficulty=problem["difficulty"],
        prompt_text=problem["prompt_text"],
    )