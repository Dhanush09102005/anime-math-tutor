from fastapi import APIRouter, HTTPException

from math_engine.verify import verify_answer
from math_engine.difficulty import next_difficulty
from personas.prompt_builder import load_persona, classify_event, build_prompt
from llm_client.hf_client import get_reaction
from routes.session import get_session
import state
from schemas import SubmitRequest, SubmitResponse

router = APIRouter()


@router.post("/submit", response_model=SubmitResponse)
def submit_answer(req: SubmitRequest):
    s = get_session(req.session_id)
    problem = s["current_problem"]

    if problem is None:
        raise HTTPException(status_code=400, detail="No active problem for this session. Call POST /problem first.")
    if problem["id"] != req.problem_id:
        raise HTTPException(status_code=409, detail="problem_id doesn't match the session's active problem (stale submit).")

    persona = load_persona(s["persona_id"])
    old_streak = s["streak"]

    if req.give_up:
        verification_result = {"correct": False, "parsed_answer": None, "mistake_type": None}
        is_repeated_mistake = False
        new_streak = 0
    else:
        verification_result = verify_answer(problem, req.answer or "")
        mistake_type = verification_result["mistake_type"]
        is_repeated_mistake = (
            not verification_result["correct"]
            and mistake_type is not None
            and mistake_type == s["last_mistake_type"]
        )
        new_streak = old_streak + 1 if verification_result["correct"] else 0

    is_topic_mastered = (
        verification_result["correct"]
        and problem["difficulty"] >= state.MASTERY_DIFFICULTY_THRESHOLD
        and not s["mastery_announced"]
    )
    if is_topic_mastered:
        s["mastery_announced"] = True

    event_category = classify_event(
        verification_result=verification_result,
        streak=new_streak,
        is_repeated_mistake=is_repeated_mistake,
        is_topic_mastered=is_topic_mastered,
        is_give_up=req.give_up,
    )

    prompt = build_prompt(persona, problem, verification_result, event_category, new_streak)

    try:
        reaction = get_reaction(prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")

    new_difficulty = next_difficulty(
        current_difficulty=problem["difficulty"],
        streak=new_streak,
        was_correct=verification_result["correct"],
    )

    s["streak"] = new_streak
    s["difficulty"] = new_difficulty
    s["last_mistake_type"] = None if verification_result["correct"] else verification_result["mistake_type"]
    s["current_problem"] = None

    return SubmitResponse(
        correct=verification_result["correct"],
        mistake_type=verification_result["mistake_type"],
        correct_answer=str(problem["canonical_answer"]),
        event_category=event_category,
        reaction=reaction,
        streak=new_streak,
        difficulty=new_difficulty,
    )