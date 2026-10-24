"""persist active problems and conversation history

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("consecutive_wrong", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "sessions",
        sa.Column("current_problem", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "conversation_history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("sessions", "conversation_history")
    op.drop_column("sessions", "current_problem")
    op.drop_column("sessions", "consecutive_wrong")
