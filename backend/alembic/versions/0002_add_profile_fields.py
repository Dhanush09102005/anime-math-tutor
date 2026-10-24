"""add display_name and avatar_url to users

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-23

Adds the two profile fields referenced by db/models.py's User model
(display_name, avatar_url) and by crud.update_user_profile — both were
already in the ORM model but had never had a migration generated for
them, so the live schema was out of sync with the model. Both nullable:
existing rows (and every current registration/OAuth flow) never set
these at creation time, so there's no backfill needed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "display_name")
