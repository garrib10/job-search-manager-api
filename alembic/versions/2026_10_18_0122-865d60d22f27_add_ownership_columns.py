"""add ownership columns

Revision ID: 865d60d22f27
Revises: 2bf55ef584f4
Create Date: 2026-10-18 01:22:37.590313

Stage 1 of 2 for record ownership. Adds a NULLABLE user_id to companies and
job_applications, with an index and a named foreign key to users.id.

The columns start nullable so this revision succeeds on databases that already
have rows. Existing rows keep user_id = NULL until stage 2 (add88b8a484a)
assigns an owner and makes the column NOT NULL. See
docs/database-migrations.md, "Ownership migration".

Downgrade drops the columns, which permanently removes any owner assignments.
The companies and applications themselves are kept.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "865d60d22f27"
down_revision: Union[str, Sequence[str], None] = "2bf55ef584f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OWNED_TABLES = ("companies", "job_applications")


def upgrade() -> None:
    """Add nullable user_id columns with an index and foreign key."""
    for table in OWNED_TABLES:
        op.add_column(table, sa.Column("user_id", sa.Integer(), nullable=True))
        op.create_index(f"ix_{table}_user_id", table, ["user_id"], unique=False)
        op.create_foreign_key(
            f"fk_{table}_user_id_users",
            table,
            "users",
            ["user_id"],
            ["id"],
        )


def downgrade() -> None:
    """Remove the ownership columns. Owner assignments are lost; rows are kept."""
    # WHY:
    # On MySQL the foreign key must be dropped before the index it uses.
    for table in reversed(OWNED_TABLES):
        op.drop_constraint(f"fk_{table}_user_id_users", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_user_id", table_name=table)
        op.drop_column(table, "user_id")
