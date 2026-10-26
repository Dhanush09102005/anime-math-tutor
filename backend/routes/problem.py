import json

from fastapi import APIRouter, Depends, HTTPException
from openai import APIError
from sqlalchemy.orm import Session

from math_engine.generate import (
    HYBRID_PROPOSAL_INSTRUCTIONS,
    generate_problem,
    generate_problem_from_proposal,
)
from llm_client.hf_client import propose_problem_parameters
from routes.session import get_session
from db.database import get_db
from db import crud
from db.models import User
from auth.dependencies import get_current_user
from schemas import ProblemRequest, ProblemResponse

router = APIRouter()


@router.post("/problem", response_model=ProblemResponse)
def get_problem(
    req: ProblemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = get_session(req.session_id, current_user, db)

    if req.topic:
        s["topic"] = req.topic
        s["current_problem"] = None
        # Persist the topic change so it survives a restart
        crud.update_session(
            db,
            session_id=req.session_id,
            difficulty=s["difficulty"],
            streak=s["streak"],
            mastery_announced=s["mastery_announced"],
            last_mistake_type=s["last_mistake_type"],
            topic=s["topic"],
            current_problem=None,
            conversation_history=s["conversation_history"],
            consecutive_wrong=s["consecutive_wrong"],
        )

    generation_mode = "procedural"
    if s["topic"] in HYBRID_PROPOSAL_INSTRUCTIONS:
        try:
            proposal = propose_problem_parameters(
                s["topic"],
                s["difficulty"],
                HYBRID_PROPOSAL_INSTRUCTIONS[s["topic"]],
            )
            problem = generate_problem_from_proposal(s["topic"], s["difficulty"], proposal)
            generation_mode = "hybrid"
        except (ValueError, KeyError, TypeError, json.JSONDecodeError, APIError):
            problem = generate_problem(s["topic"], s["difficulty"])
            generation_mode = "procedural_fallback"
    else:
        problem = generate_problem(s["topic"], s["difficulty"])
    problem["generation_mode"] = generation_mode
    crud.update_session(
        db,
        session_id=req.session_id,
        difficulty=s["difficulty"],
        streak=s["streak"],
        mastery_announced=s["mastery_announced"],
        last_mistake_type=s["last_mistake_type"],
        topic=s["topic"],
        current_problem=problem,
        conversation_history=s["conversation_history"],
        consecutive_wrong=s["consecutive_wrong"],
    )
    s["current_problem"] = problem  # canonical_answer stays server-side only

    return ProblemResponse(
        problem_id=problem["id"],
        topic=problem["topic"],
        difficulty=problem["difficulty"],
        prompt_text=problem["prompt_text"],
        answer_shape=problem["answer_shape"],
        generation_mode=generation_mode,
    )
