from fastapi import APIRouter, HTTPException

from math_engine.verify import verify_answer
from math_engine.difficulty import next_difficulty
from personas.prompt_builder import load_persona, classify_event, build_system_prompt, build_turn, format_answer_for_display
from llm_client.hf_client import get_reaction
from routes.session import get_session
import state
import db.database as db
from schemas import SubmitRequest, SubmitResponse

router = APIRouter()


@router.post("/submit", response_model=SubmitResponse)
def submit_answer(req: SubmitRequest):
    s = get_session(req.session_id)
    problem = s["current_problem"]

    if problem is None:
        raise HTTPException(status_code=400, detail="No active problem. Call POST /problem first.")
    if problem["id"] != req.problem_id:
        raise HTTPException(status_code=409, detail="problem_id doesn't match active problem (stale submit).")

    persona = load_persona(s["persona_id"])
    old_streak = s["streak"]
    old_consecutive_wrong = s.get("consecutive_wrong", 0)

    # ── Verify ────────────────────────────────────────────────────────────────
    if req.give_up:
        verification_result = {"correct": False, "parsed_answer": None, "mistake_type": None, "not_serious": False}
        not_serious = False          # ← new line, that's it
        is_repeated_mistake = False
        new_streak = 0
        new_consecutive_wrong = old_consecutive_wrong + 1
    else:
        verification_result = verify_answer(problem, req.answer or "")
        not_serious = verification_result.get("not_serious", False)
        mistake_type = verification_result["mistake_type"]

        is_repeated_mistake = (
            not not_serious
            and not verification_result["correct"]
            and mistake_type is not None
            and mistake_type == s["last_mistake_type"]
        )

        if not_serious:
            new_streak = old_streak
            new_consecutive_wrong = old_consecutive_wrong  # doesn't count
        elif verification_result["correct"]:
            new_streak = old_streak + 1
            new_consecutive_wrong = 0  # reset on correct
        else:
            new_streak = 0
            new_consecutive_wrong = old_consecutive_wrong + 1

    # ── Update difficulty (before classify so milestone can be detected) ────────
    new_difficulty = next_difficulty(
        current_difficulty=problem["difficulty"],
        streak=new_streak,
        was_correct=verification_result["correct"],
    ) if not not_serious else problem["difficulty"]

    is_difficulty_milestone = (
        not not_serious
        and verification_result["correct"]
        and new_difficulty != problem["difficulty"]
        and new_difficulty in (3, 5, 7, 9)  # meaningful thresholds only
    )

    # ── Classify ──────────────────────────────────────────────────────────────
    is_topic_mastered = (
        not not_serious
        and verification_result["correct"]
        and problem["difficulty"] >= state.MASTERY_DIFFICULTY_THRESHOLD
        and not s["mastery_announced"]
    )
    if is_topic_mastered:
        s["mastery_announced"] = True

    event_category = classify_event(
        verification_result=verification_result,
        streak=new_streak,
        consecutive_wrong=new_consecutive_wrong,
        is_repeated_mistake=is_repeated_mistake,
        is_topic_mastered=is_topic_mastered,
        is_difficulty_milestone=is_difficulty_milestone,
        is_give_up=req.give_up,
    )

    # ── Build turn + call LLM ─────────────────────────────────────────────────
    system_prompt = build_system_prompt(persona)
    user_turn = build_turn(
        persona=persona,
        problem=problem,
        verification_result=verification_result,
        event_category=event_category,
        streak=new_streak,
        consecutive_wrong=new_consecutive_wrong,
        new_difficulty=new_difficulty,
        old_difficulty=problem["difficulty"],
    )

    # Append user turn to history, then call LLM
    history = s.get("conversation_history", [])
    history.append({"role": "user", "content": user_turn})

    # Cap history to last HISTORY_MAX_TURNS * 2 messages (user+assistant pairs)
    max_messages = state.HISTORY_MAX_TURNS * 2
    if len(history) > max_messages:
        history = history[-max_messages:]

    try:
        reaction = get_reaction(system_prompt, history)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")

    # Append assistant response to history
    history.append({"role": "assistant", "content": reaction})

    # ── Persist state ─────────────────────────────────────────────────────────
    s["streak"] = new_streak
    s["consecutive_wrong"] = new_consecutive_wrong
    s["difficulty"] = new_difficulty
    s["conversation_history"] = history  # memory only — never goes to DB

    if not not_serious:
        s["last_mistake_type"] = None if verification_result["correct"] else verification_result["mistake_type"]
        s["current_problem"] = None
        db.update_session(
            session_id=req.session_id,
            difficulty=new_difficulty,
            streak=new_streak,
            mastery_announced=s["mastery_announced"],
            last_mistake_type=s["last_mistake_type"],
            topic=s["topic"],
        )
        db.log_attempt(
            session_id=req.session_id,
            problem_id=problem["id"],
            topic=problem["topic"],
            difficulty=problem["difficulty"],
            correct=verification_result["correct"],
            mistake_type=verification_result["mistake_type"],
            event_category=event_category,
        )

    return SubmitResponse(
        correct=verification_result["correct"],
        mistake_type=verification_result["mistake_type"],
        correct_answer=format_answer_for_display(problem["canonical_answer"]),
        event_category=event_category,
        reaction=reaction,
        streak=new_streak,
        difficulty=new_difficulty,
    )
