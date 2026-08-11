import json
import random
from pathlib import Path

PERSONAS_DIR = Path(__file__).parent


def load_persona(persona_id: str) -> dict:
    """
    Loads a persona JSON file by id, e.g. load_persona("kakashi").
    """
    path = PERSONAS_DIR / f"{persona_id}.json"
    if not path.exists():
        raise ValueError(f"No persona found for id: {persona_id}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def classify_event(verification_result: dict, streak: int, is_repeated_mistake: bool,
                    is_topic_mastered: bool, is_give_up: bool) -> str:
    """
    Decides which reaction_bank category this moment falls into.
    This is the single source of truth for event classification —
    both the text reaction and the mood/image system should
    call this same function so they never disagree with each other.

    not_serious takes priority over everything else except give_up —
    we don't want a garbage input accidentally triggering topic_mastered etc.
    """
    if is_give_up:
        return "give_up_request"
    if verification_result.get("not_serious"):
        return "not_serious"
    if is_topic_mastered:
        return "topic_mastered"
    if not verification_result["correct"]:
        if is_repeated_mistake:
            return "repeated_mistake"
        return "incorrect"
    # correct answer from here on
    if streak >= 3:
        return "correct_streak"
    return "correct_first_try"


def build_prompt(persona: dict, problem: dict, verification_result: dict,
                  event_category: str, streak: int) -> str:
    """
    Assembles the full prompt sent to the Claude API.
    The LLM's ONLY job is persona + explanation — it must never
    re-derive or contradict the verified math result.
    """
    example_lines = persona["reaction_bank"].get(event_category, [])
    example_line = random.choice(example_lines) if example_lines else ""

    system_context = f"""You are {persona['name']} ({persona['title']}), acting as a math tutor.

CORE PHILOSOPHY: {persona['core_philosophy']}

TONE: {persona['tone']}

SPEECH STYLE: {persona['speech_patterns']['sentence_style']}
Verbal tics to weave in naturally (don't force all of them every time):
{chr(10).join('- ' + tic for tic in persona['speech_patterns']['verbal_tics'])}

TEACHING STYLE:
- Hints: {persona['teaching_style']['hint_approach']}
- Explaining concepts: {persona['teaching_style']['explanation_approach']}

You can draw on these flavor references when natural, don't force them every time:
{chr(10).join('- ' + ref for ref in persona['in_universe_refs'])}

Here's an example of the kind of line that fits this moment (don't repeat it verbatim, just match its energy):
"{example_line}"
"""

    not_serious = verification_result.get("not_serious", False)
    raw_input_note = ""
    if not_serious:
        raw_input = verification_result.get("parsed_answer")
        if raw_input is None:
            raw_input_note = "The student typed something unparseable — not a real number answer at all."
        else:
            raw_input_note = (
                f"The student typed an expression ('{raw_input}') instead of a plain number. "
                f"The value {'happens to be correct' if verification_result['correct'] else 'is also wrong'}. "
                "Either way, they're being cheeky instead of giving a direct answer."
            )

    situation = f"""
CURRENT SITUATION (already verified — do not recompute or contradict this):
Problem: {problem['prompt_text']}
Correct answer: {problem['canonical_answer']}
Student's answer: {verification_result.get('parsed_answer')}
Was the student correct: {verification_result['correct']}
Current streak: {streak}
Event type: {event_category}
{raw_input_note}

Respond in character as {persona['name']}, reacting to this specific result. If the event
type is 'not_serious', react with bored dismissal — tell them to stop messing around and
give a proper answer. Do not treat it as a correct or incorrect answer, just call them out
in character. Otherwise, if the student was wrong, briefly explain the correct approach
without giving away future problems. Keep it to 2-4 sentences — quick reaction, not a lecture.
"""

    return system_context + situation