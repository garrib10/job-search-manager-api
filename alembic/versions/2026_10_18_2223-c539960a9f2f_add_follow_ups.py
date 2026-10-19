"""add follow ups

Revision ID: c539960a9f2f
Revises: 9e9a352c0176
Create Date: 2026-10-18 22:23:00.000000

Adds the follow_ups table: to-dos attached to a job application, with a due
date, a completed flag, and the time they were completed. Each follow-up
belongs to whoever owns its application, and is deleted with it
(ON DELETE CASCADE).

Upgrade only creates a new table; existing data is untouched.

WARNING: downgrade drops the follow_ups table and every follow-up in it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c539960a9f2f"
down_revision: Union[str, Sequence[str], None] = "9e9a352c0176"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the follow_ups table."""
    op.create_table(
        "follow_ups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("completed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["job_applications.id"],
            name="fk_follow_ups_application_id_job_applications",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_follow_ups_application_id", "follow_ups", ["application_id"], unique=False)


def downgrade() -> None:
    """Drop the follow_ups table. Every follow-up is permanently deleted."""
    op.drop_table("follow_ups")
