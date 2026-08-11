DEFAULT_TOPIC = "linear_equations"
DEFAULT_DIFFICULTY = 1
MASTERY_DIFFICULTY_THRESHOLD = 8

# session_id -> session state dict. In-memory only — wiped on server restart.
# Lives here (not inside a route file) so /session, /problem, and /submit
# can all read/write the same dict instead of each having their own copy.
SESSIONS: dict = {}


def new_session_state(persona_id: str) -> dict:
    return {
        "persona_id": persona_id,
        "topic": DEFAULT_TOPIC,
        "difficulty": DEFAULT_DIFFICULTY,
        "streak": 0,
        "current_problem": None,
        "last_mistake_type": None,
        "mastery_announced": False,
    }