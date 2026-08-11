"""
SQLite persistence layer.

Two tables:
  sessions  — one row per session, mirrors the in-memory session dict
  attempts  — one row per /submit call (excluding not_serious non-answers)

The in-memory SESSIONS dict in state.py stays as a request-scoped cache —
reads hit memory first, writes go to both memory and DB.
current_problem is NOT stored in DB (it contains SymPy objects that don't
serialize cleanly, and it's ephemeral within a single problem cycle anyway).
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "tutor.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # lets us access columns by name
    conn.execute("PRAGMA journal_mode=WAL")  # safe for concurrent reads
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Called once at app startup."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id        TEXT PRIMARY KEY,
                persona_id        TEXT NOT NULL,
                topic             TEXT NOT NULL,
                difficulty        INTEGER NOT NULL,
                streak            INTEGER NOT NULL DEFAULT 0,
                mastery_announced INTEGER NOT NULL DEFAULT 0,
                last_mistake_type TEXT,
                created_at        TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS attempts (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     TEXT NOT NULL,
                problem_id     TEXT NOT NULL,
                topic          TEXT NOT NULL,
                difficulty     INTEGER NOT NULL,
                correct        INTEGER NOT NULL,
                mistake_type   TEXT,
                event_category TEXT NOT NULL,
                timestamp      TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            );
        """)


# ── Session operations ────────────────────────────────────────────────────────

def create_session(session_id: str, persona_id: str, topic: str, difficulty: int) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO sessions
               (session_id, persona_id, topic, difficulty, streak, mastery_announced, last_mistake_type)
               VALUES (?, ?, ?, ?, 0, 0, NULL)""",
            (session_id, persona_id, topic, difficulty),
        )


def load_session(session_id: str) -> dict | None:
    """Returns session as a dict, or None if not found."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    if row is None:
        return None
    return {
        "persona_id":        row["persona_id"],
        "topic":             row["topic"],
        "difficulty":        row["difficulty"],
        "streak":            row["streak"],
        "mastery_announced": bool(row["mastery_announced"]),
        "last_mistake_type": row["last_mistake_type"],
        "current_problem":   None,   # never persisted — always starts empty
    }


def update_session(session_id: str, difficulty: int, streak: int,
                   mastery_announced: bool, last_mistake_type: str | None,
                   topic: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """UPDATE sessions
               SET difficulty = ?, streak = ?, mastery_announced = ?,
                   last_mistake_type = ?, topic = ?
               WHERE session_id = ?""",
            (difficulty, streak, int(mastery_announced),
             last_mistake_type, topic, session_id),
        )


# ── Attempt logging ───────────────────────────────────────────────────────────

def log_attempt(session_id: str, problem_id: str, topic: str, difficulty: int,
                correct: bool, mistake_type: str | None, event_category: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO attempts
               (session_id, problem_id, topic, difficulty, correct, mistake_type, event_category)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, problem_id, topic, difficulty,
             int(correct), mistake_type, event_category),
        )
