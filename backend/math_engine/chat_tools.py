"""
Wraps math_engine's existing generate_problem/verify_answer as LLM tool-calls,
for v2.2's chat mode. Neither function is modified — this file only adds a
calling convention on top of them (JSON-schema tool defs + a dispatcher that
executes the right one and serializes the result for the LLM).

Correctness principle carried over unchanged from the Q&A pipeline: the LLM
never decides whether an answer is right. It can talk freely, but the moment
correctness needs judging, it MUST call check_answer and report what comes
back — it doesn't get to assert an answer is correct on its own authority.
The chat system prompt (prompt_builder.build_chat_system_prompt) is what
actually enforces this at the instruction level; this file just makes the
tool available and honest about what it returns.
"""

from math_engine.generate import generate_problem
from math_engine.verify import verify_answer
from personas.prompt_builder import format_answer_for_display

# ─────────────────────────────────────────────────────────────────────────────
# Tool schemas — OpenAI-compatible function-calling format. Sent to the LLM
# alongside the system prompt so it knows what it can call and with what args.
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
                "because the session is new or a message came in — respond to what "
                "the student actually said first. If they said something personal, "
                "off-topic, or unrelated to math, just talk with them. Do not invent "
                "a problem yourself — when you do decide to give one, always call "
                "this tool rather than writing one from memory."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
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
                "your reaction on what it returns. If no problem is active yet, this "
                "will return an error — call get_next_problem first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "The student's answer, exactly as they stated it (e.g. '5', '2, 3', 'x = -4').",
                    }
                },
                "required": ["answer"],
            },
        },
    },
]


def execute_tool(tool_name: str, arguments: dict, session: dict) -> dict:
    """
    Executes a tool call against the given session, mutating session state
    where relevant (current_problem, streak, consecutive_wrong), and returns
    a JSON-serializable result dict to feed back to the LLM as the tool
    result. Sympy objects are never returned raw — always passed through
    format_answer_for_display first, since tool results get serialized to a
    plain string for the model.
    """
    if tool_name == "get_next_problem":
        return _get_next_problem(session)
    elif tool_name == "check_answer":
        return _check_answer(session, arguments.get("answer", ""))
    else:
        return {"error": f"Unknown tool: {tool_name}"}


def _get_next_problem(session: dict) -> dict:
    problem = generate_problem(session["topic"], session["difficulty"])
    session["current_problem"] = problem

    return {
        "prompt_text": problem["prompt_text"],
        "difficulty": problem["difficulty"],
        "topic": problem["topic"],
        # canonical_answer is deliberately NOT included here — the LLM should
        # never see the answer ahead of the student, same principle as the
        # Q&A pipeline never sending it to the frontend.
    }


def _check_answer(session: dict, answer: str) -> dict:
    problem = session.get("current_problem")
    if problem is None:
        return {"error": "No active problem. Call get_next_problem first."}

    result = verify_answer(problem, answer)

    # Update streak/difficulty the same way the Q&A /submit route does, so
    # chat mode and Q&A mode behave consistently if a session ever crossed
    # between them (it currently can't — mode is fixed at session creation —
    # but keeping the logic identical avoids two diverging sources of truth).
    if not result.get("not_serious"):
        if result["correct"]:
            session["streak"] = session.get("streak", 0) + 1
            session["consecutive_wrong"] = 0
        else:
            session["streak"] = 0
            session["consecutive_wrong"] = session.get("consecutive_wrong", 0) + 1

    return {
        "correct": result["correct"],
        "mistake_type": result["mistake_type"],
        "not_serious": result.get("not_serious", False),
        "student_answer": format_answer_for_display(result.get("parsed_answer")),
        "correct_answer": format_answer_for_display(problem["canonical_answer"]),
        "streak": session.get("streak", 0),
    }
