"""
PostgreSQL persistence layer via SQLAlchemy.

Replaces the old raw-sqlite3 module. Schema is now owned by Alembic
migrations (see alembic/), not created here — this module only wires up
the engine and per-request session factory.

The in-memory SESSIONS dict in state.py stays as a request-scoped cache —
reads hit memory first, writes go to both memory and DB.
current_problem is still NOT stored in DB (SymPy objects don't serialize
cleanly, and it's ephemeral within a single problem cycle anyway).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ["DATABASE_URL"]  # e.g. postgresql+psycopg2://tutor:pass@localhost:5432/tutor

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a request-scoped DB session, closes after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
