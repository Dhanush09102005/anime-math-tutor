DEFAULT_TOPIC = "linear_equations"
DEFAULT_DIFFICULTY = 1
MASTERY_DIFFICULTY_THRESHOLD = 8

# In-memory session cache — primary store for active request handling.
# On server restart, sessions are reloaded from SQLite on first access.
# current_problem is never persisted — it's ephemeral within one problem cycle.
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