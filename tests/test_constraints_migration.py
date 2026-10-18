"""
Tests for migration 9e9a352c0176 (delete and uniqueness rules), run against
the disposable test database with data created before the migration.
"""

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from tests.conftest import test_engine
from tests.migration_utils import alembic, current_revision, execute, query, scalar

BEFORE = "add88b8a484a"
REVISION = "9e9a352c0176"


def seed_owned_data() -> dict[str, int]:
    """Two users with their own companies, applications, and interviews."""
    for email in ("a@example.com", "b@example.com"):
        execute("INSERT INTO users (email, hashed_password, is_active) VALUES (:e, 'x', 1)", e=email)

    a = scalar("SELECT id FROM users WHERE email = 'a@example.com'")
    b = scalar("SELECT id FROM users WHERE email = 'b@example.com'")

    execute("INSERT INTO companies (id, name, user_id) VALUES (1, 'A Corp', :a), (2, 'B Corp', :b)", a=a, b=b)
    execute(
        "INSERT INTO job_applications (id, job_title, job_url, status, date_saved, company_id, user_id) VALUES "
        "(10, 'Engineer', 'https://example.com/shared', 'saved', '2026-10-01', 1, :a), "
        "(11, 'Engineer', 'https://example.com/only-b', 'saved', '2026-10-01', 2, :b)",
        a=a,
        b=b,
    )
    execute(
        "INSERT INTO interviews (id, interview_type, status, outcome, scheduled_at, application_id) VALUES "
        "(100, 'technical', 'scheduled', 'pending', '2026-11-01 15:00:00', 10), "
        "(101, 'hr', 'scheduled', 'pending', '2026-11-02 15:00:00', 10), "
        "(102, 'hr', 'scheduled', 'pending', '2026-11-03 15:00:00', 11)"
    )

    return {"a": a, "b": b}


def test_upgrade_keeps_data_and_applies_new_rules(empty_database):
    alembic("upgrade", BEFORE)
    users = seed_owned_data()
    before = query("SELECT id, job_url, user_id FROM job_applications ORDER BY id")

    alembic("upgrade", REVISION)

    assert current_revision() == REVISION
    assert query("SELECT id, job_url, user_id FROM job_applications ORDER BY id") == before

    unique_keys = {c["name"]: c["column_names"] for c in inspect(test_engine).get_unique_constraints("job_applications")}
    assert unique_keys.get("uq_job_applications_user_id_job_url") == ["user_id", "job_url"]
    assert ["job_url"] not in unique_keys.values()

    # Another user may now track the same URL...
    execute(
        "INSERT INTO job_applications (job_title, job_url, status, date_saved, company_id, user_id) "
        "VALUES ('Engineer', 'https://example.com/shared', 'saved', '2026-10-02', 2, :b)",
        b=users["b"],
    )

    # ...but the same user still can't track it twice.
    with pytest.raises(IntegrityError):
        execute(
            "INSERT INTO job_applications (job_title, job_url, status, date_saved, company_id, user_id) "
            "VALUES ('Engineer', 'https://example.com/shared', 'saved', '2026-10-02', 1, :a)",
            a=users["a"],
        )


def test_deleting_an_application_row_cascades_to_its_interviews(empty_database):
    alembic("upgrade", BEFORE)
    seed_owned_data()
    alembic("upgrade", REVISION)

    execute("DELETE FROM job_applications WHERE id = 10")

    assert query("SELECT id FROM interviews ORDER BY id") == [(102,)]


def test_downgrade_stops_when_users_share_a_job_url(empty_database):
    alembic("upgrade", BEFORE)
    users = seed_owned_data()
    alembic("upgrade", REVISION)
    execute(
        "INSERT INTO job_applications (job_title, job_url, status, date_saved, company_id, user_id) "
        "VALUES ('Engineer', 'https://example.com/shared', 'saved', '2026-10-02', 2, :b)",
        b=users["b"],
    )

    with pytest.raises(RuntimeError, match="tracked by more than one user"):
        alembic("downgrade", BEFORE)

    assert current_revision() == REVISION
    unique_keys = {c["name"] for c in inspect(test_engine).get_unique_constraints("job_applications")}
    assert "uq_job_applications_user_id_job_url" in unique_keys


def test_downgrade_restores_previous_constraints(empty_database):
    alembic("upgrade", BEFORE)
    seed_owned_data()
    alembic("upgrade", REVISION)

    alembic("downgrade", BEFORE)

    inspector = inspect(test_engine)
    unique_columns = [c["column_names"] for c in inspector.get_unique_constraints("job_applications")]
    assert ["job_url"] in unique_columns
    assert ["user_id", "job_url"] not in unique_columns

    interview_fk = next(
        fk for fk in inspector.get_foreign_keys("interviews") if fk["constrained_columns"] == ["application_id"]
    )
    assert interview_fk["options"].get("ondelete") is None
    assert scalar("SELECT COUNT(*) FROM interviews") == 3
