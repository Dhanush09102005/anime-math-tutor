"""add mode column to sessions

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-27

Adds `mode` (varchar, default 'qna') to the sessions table.
Previously only stored in-memory — lost on server restart.
server_default ensures existing rows get 'qna' without a backfill scan.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column(
            "mode",
            sa.String(),
            nullable=False,
            server_default="qna",   # backfills existing rows immediately
        ),
    )


def downgrade() -> None:
    op.drop_column("sessions", "mode")
