"""enforce ownership

Revision ID: add88b8a484a
Revises: 865d60d22f27
Create Date: 2026-10-18 01:23:38.808911

Stage 2 of 2 for record ownership. Assigns an owner to any company or job
application that has none, checks the result, then makes user_id NOT NULL.

On a database with no unowned rows (including an empty one) it only adds the
NOT NULL constraints.

If unowned rows exist, the owner must be chosen explicitly:

    alembic -x owner_email=owner@example.com upgrade head

Before changing anything, the migration checks that:

- an owner was given whenever unowned rows exist,
- that owner exists and is active,
- every job application would end up with the same owner as its company.

If any check fails it raises an error and changes nothing; the database stays
at stage 1 (865d60d22f27) with nullable columns, so the problem can be fixed
and the command re-run. It never picks an owner on its own and never deletes
rows. See docs/database-migrations.md, "Ownership migration".

Downgrade only makes user_id nullable again; owner assignments are kept.
"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add88b8a484a"
down_revision: Union[str, Sequence[str], None] = "865d60d22f27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OWNED_TABLES = ("companies", "job_applications")


class OwnershipMigrationError(RuntimeError):
    """Raised when existing rows cannot be given an owner safely."""


def owned_table(table: str) -> str:
    """Only the fixed table names in OWNED_TABLES are ever placed into SQL."""
    if table not in OWNED_TABLES:
        raise ValueError(f"Unexpected table name: {table!r}")

    return table


def count_unowned(connection, table: str) -> int:
    # Table name is checked against OWNED_TABLES; no user input reaches the SQL.
    sql = f"SELECT COUNT(*) FROM {owned_table(table)} WHERE user_id IS NULL"  # nosec B608
    return connection.execute(sa.text(sql)).scalar_one()


def resolve_owner_id(connection, owner_email: str) -> int:
    owner = connection.execute(
        sa.text("SELECT id, is_active FROM users WHERE email = :email"),
        {"email": owner_email},
    ).one_or_none()

    if owner is None:
        raise OwnershipMigrationError(
            f"No user has the email {owner_email!r}. Nothing was changed. "
            "Register that account first, or pass the email of an existing user."
        )

    if not owner.is_active:
        raise OwnershipMigrationError(
            f"The user {owner_email!r} is inactive. Nothing was changed. "
            "Choose an active account to own the existing records."
        )

    return owner.id


def find_owner_mismatches(connection, owner_id: int | None) -> list[int]:
    """IDs of applications whose owner would differ from their company's owner."""
    rows = connection.execute(
        sa.text(
            "SELECT ja.id FROM job_applications ja "
            "JOIN companies c ON c.id = ja.company_id "
            "WHERE COALESCE(ja.user_id, :owner_id) <> COALESCE(c.user_id, :owner_id) "
            "ORDER BY ja.id"
        ),
        {"owner_id": owner_id},
    )

    return [row.id for row in rows]


def upgrade() -> None:
    """Assign owners to unowned rows (if any) after validation, then enforce NOT NULL."""
    connection = op.get_bind()
    owner_email = context.get_x_argument(as_dictionary=True).get("owner_email")

    unowned = {table: count_unowned(connection, table) for table in OWNED_TABLES}
    owner_id = None

    if any(unowned.values()):
        if not owner_email:
            raise OwnershipMigrationError(
                f"{unowned['companies']} companies and {unowned['job_applications']} job applications "
                "have no owner (user_id is NULL). Nothing was changed. Choose the account that should "
                "own them and re-run: alembic -x owner_email=<email> upgrade head"
            )

        owner_id = resolve_owner_id(connection, owner_email)

    mismatches = find_owner_mismatches(connection, owner_id)

    if mismatches:
        shown = ", ".join(str(application_id) for application_id in mismatches[:10])
        raise OwnershipMigrationError(
            f"{len(mismatches)} job application(s) would not have the same owner as their company "
            f"(application IDs: {shown}). Nothing was changed. Fix their user_id, or their company's, "
            "and re-run."
        )

    if owner_id is not None:
        for table in OWNED_TABLES:
            # Table name is checked against OWNED_TABLES; the owner ID is a bound parameter.
            sql = f"UPDATE {owned_table(table)} SET user_id = :owner_id WHERE user_id IS NULL"  # nosec B608
            connection.execute(sa.text(sql), {"owner_id": owner_id})

    still_unowned = {table: count_unowned(connection, table) for table in OWNED_TABLES}

    if any(still_unowned.values()) or find_owner_mismatches(connection, None):
        raise OwnershipMigrationError(
            "Ownership check failed after assigning owners; NOT NULL was not applied. "
            "Inspect the user_id columns before re-running."
        )

    for table in OWNED_TABLES:
        op.alter_column(table, "user_id", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    """Make user_id nullable again. Owner assignments are kept."""
    for table in reversed(OWNED_TABLES):
        op.alter_column(table, "user_id", existing_type=sa.Integer(), nullable=True)
