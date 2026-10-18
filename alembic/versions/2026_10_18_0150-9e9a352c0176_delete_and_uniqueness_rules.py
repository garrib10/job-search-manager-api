"""delete and uniqueness rules

Revision ID: 9e9a352c0176
Revises: add88b8a484a
Create Date: 2026-10-18 01:50:10.000000

- job_applications.job_url: unique per user (user_id, job_url) instead of
  globally unique, so different users can track the same posting.
- interviews.application_id: foreign key recreated with ON DELETE CASCADE,
  so deleting an application deletes its interviews.

The baseline created both constraints without explicit names, so MySQL named
them (normally `job_url` and `interviews_ibfk_1`). This migration looks the
existing constraints up by their columns instead of assuming those names.

Upgrade is safe on existing data: the old global unique key guarantees there
are no duplicates per user. Downgrade restores the global unique key and stops
with a clear error, changing nothing, if two users track the same job URL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9e9a352c0176"
down_revision: Union[str, Sequence[str], None] = "add88b8a484a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PER_USER_UNIQUE = "uq_job_applications_user_id_job_url"
CASCADE_FK = "fk_interviews_application_id_job_applications"


def global_job_url_unique_name(inspector) -> str:
    """Name of the unique key on job_applications(job_url) alone."""
    for constraint in inspector.get_unique_constraints("job_applications"):
        if constraint["column_names"] == ["job_url"]:
            return constraint["name"]

    for index in inspector.get_indexes("job_applications"):
        if index["unique"] and index["column_names"] == ["job_url"]:
            return index["name"]

    raise RuntimeError("No unique key on job_applications(job_url) was found; nothing was changed.")


def interview_application_fk_name(inspector) -> str:
    """Name of the foreign key from interviews.application_id to job_applications."""
    for foreign_key in inspector.get_foreign_keys("interviews"):
        if foreign_key["constrained_columns"] == ["application_id"] and foreign_key["referred_table"] == "job_applications":
            return foreign_key["name"]

    raise RuntimeError("No foreign key on interviews(application_id) was found; nothing was changed.")


def upgrade() -> None:
    """Make job_url unique per user and cascade interview deletes."""
    inspector = sa.inspect(op.get_bind())
    old_unique = global_job_url_unique_name(inspector)
    old_fk = interview_application_fk_name(inspector)

    # WHY:
    # Create the per-user key before dropping the global one, so job_url is
    # never left without a uniqueness rule.
    op.create_unique_constraint(PER_USER_UNIQUE, "job_applications", ["user_id", "job_url"])
    op.drop_constraint(old_unique, "job_applications", type_="unique")

    op.drop_constraint(old_fk, "interviews", type_="foreignkey")
    op.create_foreign_key(
        CASCADE_FK,
        "interviews",
        "job_applications",
        ["application_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Restore the global job_url unique key and the non-cascading foreign key."""
    connection = op.get_bind()
    shared_urls = connection.execute(
        sa.text("SELECT COUNT(*) FROM (SELECT job_url FROM job_applications GROUP BY job_url HAVING COUNT(*) > 1) d")
    ).scalar_one()

    if shared_urls:
        raise RuntimeError(
            f"{shared_urls} job URL(s) are tracked by more than one user, so job_url can't be made "
            "globally unique again. Nothing was changed."
        )

    op.drop_constraint(CASCADE_FK, "interviews", type_="foreignkey")
    op.create_foreign_key(None, "interviews", "job_applications", ["application_id"], ["id"])

    op.create_unique_constraint(None, "job_applications", ["job_url"])
    op.drop_constraint(PER_USER_UNIQUE, "job_applications", type_="unique")
