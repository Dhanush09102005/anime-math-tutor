import json
import random
from pathlib import Path

PERSONAS_DIR = Path(__file__).parent


def format_answer_for_display(value) -> str:
    """
    Formats a canonical/parsed answer for display — in API responses and in
    the LLM prompt. Scalars (single_value) print as-is. Sets/lists/tuples
    (multi_value) print as a sorted, comma-separated list, so a quadratic's
    roots read as "2, 3" instead of Python's raw set repr "{2, 99}".

    vector_or_matrix and expression shapes aren't implemented yet
    (verify.py raises NotImplementedError for them), so this only needs to
    handle scalar and iterable-of-scalars for now.
    """
    if value is None:
        return "?"
    if isinstance(value, (set, frozenset, list, tuple)):
        try:
            ordered = sorted(value, key=lambda v: float(v))
        except (TypeError, ValueError):
            ordered = list(value)
        return ", ".join(str(v) for v in ordered)
    return str(value)


def load_persona(persona_id: str) -> dict:
    path = PERSONAS_DIR / f"{persona_id}.json"
    if not path.exists():
        raise ValueError(f"No persona found for id: {persona_id}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def classify_event(verification_result: dict, streak: int, consecutive_wrong: int,
                   is_repeated_mistake: bool, is_topic_mastered: bool,
                   is_difficulty_milestone: bool, is_give_up: bool) -> str:
    """
    Single source of truth for event classification.
    Priority order matters — checked top to bottom.
    """
    if is_give_up:
        return "give_up_request"
    if verification_result.get("not_serious"):
        return "not_serious"
    if is_topic_mastered:
        return "topic_mastered"

    if not verification_result["correct"]:
        if consecutive_wrong >= 4:
            return "full_frustration"
        if consecutive_wrong >= 2:
            return "frustration_warning"
        if is_repeated_mistake:
            return "repeated_mistake"
        return "incorrect"

    # Correct from here
    if streak == 1 and consecutive_wrong > 0:
        return "comeback"
    if is_difficulty_milestone:
        return "difficulty_milestone"
    if streak >= 3:
        return "correct_streak"
    return "correct_first_try"


def build_system_prompt(persona: dict) -> str:
    """
    Builds the system prompt — sent once per session as the "system" role.
    Describes who Kakashi is, how he speaks, and what his job is.
    This never changes mid-session.
    """
    return f"""You are {persona['name']} ({persona['title']}), acting as a math tutor in an ongoing session with a student.

CORE PHILOSOPHY: {persona['core_philosophy']}

TONE: {persona['tone']}

SPEECH STYLE: {persona['speech_patterns']['sentence_style']}

Verbal tics to weave in naturally — don't force all of them every time, let them emerge:
{chr(10).join('- ' + tic for tic in persona['speech_patterns']['verbal_tics'])}

TEACHING APPROACH:
- When giving hints: {persona['teaching_style']['hint_approach']}
- When explaining concepts: {persona['teaching_style']['explanation_approach']}
- On difficulty: {persona['teaching_style']['difficulty_philosophy']}

You can draw on these flavor references when they fit naturally:
{chr(10).join('- ' + ref for ref in persona['in_universe_refs'])}

RULES:
- You are in an ongoing conversation. Remember what has been said earlier in this session.
- Math results are pre-verified. Never recompute or contradict them.
- Keep responses to 2-6 sentences. Quick reactions, not lectures.
- Do not repeat the same phrasing you used earlier in the conversation.
- Never break character."""


def build_turn(persona: dict, problem: dict, verification_result: dict,
               event_category: str, streak: int, consecutive_wrong: int,
               new_difficulty: int = None, old_difficulty: int = None) -> str:
    """
    Builds the user-role message for this specific problem attempt.
    This gets appended to conversation_history before the LLM call.
    """
    example_lines = persona["reaction_bank"].get(event_category, [])
    example_line = random.choice(example_lines) if example_lines else ""

    not_serious = verification_result.get("not_serious", False)

    if not_serious:
        parsed = verification_result.get("parsed_answer")
        if parsed is None:
            input_note = "The student typed something completely unparseable — not a number at all."
        else:
            input_note = (
                f"The student typed an expression '{format_answer_for_display(parsed)}' instead of a plain number answer. "
                f"The value {'happens to equal the answer' if verification_result['correct'] else 'is also wrong'}. "
                "They are being cheeky."
            )
        return f"""[SITUATION]
Problem: {problem['prompt_text']}
Event: not_serious
{input_note}

React with bored dismissal. Tell them to stop messing around and give a proper answer.
Match this energy (don't repeat verbatim): "{example_line}"
[END SITUATION]"""

    # ── Wrong answer guidance — specific to mistake type ─────────────────────
    mistake_guidance = ""
    if not verification_result["correct"]:
        mistake_type = verification_result.get("mistake_type", "wrong")
        student_answer = format_answer_for_display(verification_result.get("parsed_answer"))
        correct_answer = format_answer_for_display(problem["canonical_answer"])

        if mistake_type == "sign_error":
            mistake_guidance = (
                f"The student got the magnitude right but the sign wrong — "
                f"they answered {student_answer} instead of {correct_answer}. "
                "Address the sign error specifically. Remind them to track which side things move to."
            )
        elif mistake_type == "arithmetic_slip":
            mistake_guidance = (
                f"The student was close — answered {student_answer}, correct was {correct_answer}. "
                "Small arithmetic slip at the end. Tell them the method was right, just sloppy execution."
            )
        elif mistake_type == "partial":
            mistake_guidance = (
                f"The student got PART of it right — answered {student_answer}, "
                f"but the full correct answer is {correct_answer} (there's more than one valid value here). "
                "Acknowledge what they got right first, then point out what's missing or extra — "
                "don't just call it wrong outright, they were partway there."
            )
        else:
            mistake_guidance = (
                f"The student answered {student_answer}, correct was {correct_answer}. "
                "Briefly explain where the approach went wrong without solving the next problem for them."
            )

    # ── Arc and milestone notes ───────────────────────────────────────────────
    arc_note = ""
    if consecutive_wrong >= 4:
        arc_note = (
            f"The student has gotten {consecutive_wrong} wrong answers in a row. "
            "Stop reacting to just this problem — tell them plainly to go back and study "
            "the fundamentals before continuing."
        )
    elif consecutive_wrong >= 2:
        arc_note = f"The student has been wrong {consecutive_wrong} times consecutively. Your patience is visibly wearing thin."
    elif event_category == "comeback":
        arc_note = "The student just got it right after a real struggle. Acknowledge the turnaround genuinely."
    elif event_category == "difficulty_milestone" and new_difficulty and old_difficulty:
        rank_names = {3: "C-rank", 5: "B-rank", 7: "A-rank", 9: "S-rank"}
        rank = rank_names.get(new_difficulty, f"difficulty {new_difficulty}")
        arc_note = (
            f"The student just crossed into {rank} territory (difficulty {old_difficulty} → {new_difficulty}). "
            "Acknowledge the progression in character — make them feel the difficulty has genuinely stepped up."
        )

    return f"""[SITUATION]
Problem: {problem['prompt_text']}
Correct answer: {format_answer_for_display(problem['canonical_answer'])}
Student's answer: {format_answer_for_display(verification_result.get('parsed_answer'))}
Result: {'CORRECT' if verification_result['correct'] else f"WRONG — mistake type: {verification_result.get('mistake_type', 'wrong')}"}
Current streak: {streak}
Event: {event_category}
{mistake_guidance}
{arc_note}

React in character. Match this energy (don't repeat verbatim): "{example_line}"
[END SITUATION]"""
