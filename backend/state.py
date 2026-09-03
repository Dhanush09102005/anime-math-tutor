DEFAULT_TOPIC = "linear_equations"
DEFAULT_DIFFICULTY = 1
MASTERY_DIFFICULTY_THRESHOLD = 8

# In-memory session cache — primary store for active request handling.
# On server restart, sessions are reloaded from Postgres on first access.
# current_problem is never persisted — it's ephemeral within one problem cycle.
SESSIONS: dict = {}


HISTORY_MAX_TURNS = 8  # keep last N exchanges in memory — caps context window cost


def new_session_state(persona_id: str) -> dict:
    return {
        "persona_id": persona_id,
        "user_id": None,  # set by routes/session.py's create_session right after this returns —
                           # every session is owned by exactly one authenticated user now
        "topic": DEFAULT_TOPIC,
        "difficulty": DEFAULT_DIFFICULTY,
        "streak": 0,
        "consecutive_wrong": 0,  # resets on correct, used for frustration arc
        "current_problem": None,
        "last_mistake_type": None,
        "mastery_announced": False,
        "conversation_history": [],  # list of {role, content} — never persisted to DB

        # v2.2 chat mode — reuses everything above (topic/difficulty/streak/
        # current_problem/conversation_history all apply directly to chat too,
        # since check_answer/get_next_problem tools read and write the same
        # fields the Q&A /submit and /problem routes already use).
        # "mode" exists only to prevent a session created for one flow being
        # driven through the other by mistake — not read by any verification
        # or generation logic.
        "mode": "qna",  # "qna" | "chat" — set once, at session creation
    }
