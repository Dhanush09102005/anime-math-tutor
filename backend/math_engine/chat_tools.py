"""
Wraps math_engine's existing generate_problem/verify_answer as LLM tool-calls,
for v2.2's chat mode.

Neither function is modified — this file only adds a calling convention on top
of them (JSON-schema tool defs + a dispatcher that executes the right one and
serializes the result for the LLM).
"""

from math_engine.generate import generate_problem
from math_engine.verify import verify_answer
from personas.prompt_builder import format_answer_for_display


# ─────────────────────────────────────────────────────────────────────────────
# Tool schemas
# ─────────────────────────────────────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_next_problem",
            "description": (
                "Generates a new math problem for the student to attempt, in the "
                "session's current topic and difficulty. ONLY call this when the "
                "student has actually asked for a problem, or has just finished one "
                "and clearly wants another. Do NOT call this automatically just "
                "because the session is new or a message came in. If the student "
                "said something personal, off-topic, or unrelated to math, just "
                "talk with them. Do not invent a problem yourself — when you do "
                "decide to give one, always call this tool."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_answer",
            "description": (
                "Checks a student's answer against the currently active problem. "
                "Call this whenever the student states an answer to check, even if "
                "phrased conversationally (e.g. 'is it 5?', 'I think x = 3'). "
                "Never judge correctness yourself — always call this tool and base "
                "your reaction on what it returns. If no problem is active yet, "
                "this will return an error."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": ["string", "number"],
                        "description": (
                            "The student's answer. It may be a number or a string. "
                            "Examples: 5, '2, 3', 'x = -4'."
                        ),
                    }
                },
                "required": ["answer"],
            },
        },
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Tool dispatcher
# ─────────────────────────────────────────────────────────────────────────────

def execute_tool(tool_name: str, arguments: dict, session: dict) -> dict:
    """
    Executes a tool call against the given session.

    Mutates session state where relevant:
    - current_problem
    - streak
    - consecutive_wrong

    Returns a JSON-serializable result for the LLM.
    """

    if tool_name == "get_next_problem":
        return _get_next_problem(session)

    elif tool_name == "check_answer":
        return _check_answer(
            session,
            arguments.get("answer", "")
        )

    else:
        return {
            "error": f"Unknown tool: {tool_name}"
        }


# ─────────────────────────────────────────────────────────────────────────────
# Generate problem
# ─────────────────────────────────────────────────────────────────────────────

def _get_next_problem(session: dict) -> dict:
    problem = generate_problem(
        session["topic"],
        session["difficulty"]
    )

    session["current_problem"] = problem

    return {
        "prompt_text": problem["prompt_text"],
        "difficulty": problem["difficulty"],
        "topic": problem["topic"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Check answer
# ─────────────────────────────────────────────────────────────────────────────

def _check_answer(session: dict, answer) -> dict:
    problem = session.get("current_problem")

    if problem is None:
        return {
            "error": "No active problem. Call get_next_problem first."
        }

    # IMPORTANT:
    # LLMs may send a simple numeric answer as a JSON number:
    #
    #     {"answer": 3}
    #
    # while verify_answer expects the student's answer as text.
    #
    # Convert everything to a string before passing it to verify_answer.
    answer = str(answer)

    result = verify_answer(problem, answer)

    # Update streak/difficulty state.
    if not result.get("not_serious"):
        if result["correct"]:
            session["streak"] = session.get("streak", 0) + 1
            session["consecutive_wrong"] = 0
        else:
            session["streak"] = 0
            session["consecutive_wrong"] = (
                session.get("consecutive_wrong", 0) + 1
            )

    return {
        "correct": result["correct"],
        "mistake_type": result["mistake_type"],
        "not_serious": result.get("not_serious", False),
        "student_answer": format_answer_for_display(
            result.get("parsed_answer")
        ),
        "correct_answer": format_answer_for_display(
            problem["canonical_answer"]
        ),
        "streak": session.get("streak", 0),
    }