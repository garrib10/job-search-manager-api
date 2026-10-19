"""
Tests for migration c539960a9f2f (add follow ups), run against the disposable
test database starting from the v0.3.0 schema with existing data.
"""

from sqlalchemy import inspect

from tests.conftest import test_engine
from tests.migration_utils import alembic, current_revision, execute, query, scalar

V030 = "9e9a352c0176"
REVISION = "c539960a9f2f"


def seed_v030_data() -> None:
    execute("INSERT INTO users (id, email, hashed_password, is_active) VALUES (1, 'a@example.com', 'x', 1)")
    execute("INSERT INTO companies (id, name, user_id) VALUES (1, 'Acme', 1)")
    execute(
        "INSERT INTO job_applications (id, job_title, job_url, status, date_saved, company_id, user_id) VALUES "
        "(10, 'Engineer', 'https://example.com/1', 'applied', '2026-10-01', 1, 1), "
        "(11, 'Analyst', 'https://example.com/2', 'saved', '2026-10-02', 1, 1)"
    )
    execute(
        "INSERT INTO interviews (id, interview_type, status, outcome, scheduled_at, application_id) VALUES "
        "(100, 'technical', 'scheduled', 'pending', '2026-11-01 15:00:00', 10)"
    )


def snapshot():
    return (
        query("SELECT id, email FROM users ORDER BY id"),
        query("SELECT id, name, user_id FROM companies ORDER BY id"),
        query("SELECT id, job_title, company_id, user_id FROM job_applications ORDER BY id"),
        query("SELECT id, application_id, scheduled_at FROM interviews ORDER BY id"),
    )


def test_upgrade_from_v030_keeps_existing_data(empty_database):
    alembic("upgrade", V030)
    seed_v030_data()
    before = snapshot()

    alembic("upgrade", REVISION)

    assert current_revision() == REVISION
    assert snapshot() == before
    assert scalar("SELECT COUNT(*) FROM follow_ups") == 0

    inspector = inspect(test_engine)
    columns = {c["name"]: c for c in inspector.get_columns("follow_ups")}
    assert {name: columns[name]["nullable"] for name in ("title", "due_date", "completed", "completed_at")} == {
        "title": False,
        "due_date": False,
        "completed": False,
        "completed_at": True,
    }
    fk = inspector.get_foreign_keys("follow_ups")[0]
    assert (fk["name"], fk["referred_table"], fk["options"].get("ondelete")) == (
        "fk_follow_ups_application_id_job_applications",
        "job_applications",
        "CASCADE",
    )


def test_new_follow_ups_default_to_open_and_cascade_with_their_application(empty_database):
    alembic("upgrade", V030)
    seed_v030_data()
    alembic("upgrade", REVISION)

    execute("INSERT INTO follow_ups (title, due_date, application_id) VALUES ('Email', '2026-11-12', 10), ('Call', '2026-11-13', 11)")
    assert query("SELECT application_id, completed FROM follow_ups ORDER BY id") == [(10, 0), (11, 0)]

    execute("DELETE FROM interviews WHERE application_id = 10")
    execute("DELETE FROM job_applications WHERE id = 10")

    assert query("SELECT application_id FROM follow_ups") == [(11,)]


def test_downgrade_drops_only_follow_ups(empty_database):
    alembic("upgrade", V030)
    seed_v030_data()
    before = snapshot()
    alembic("upgrade", REVISION)
    execute("INSERT INTO follow_ups (title, due_date, application_id) VALUES ('Email', '2026-11-12', 10)")

    alembic("downgrade", V030)

    assert "follow_ups" not in inspect(test_engine).get_table_names()
    assert snapshot() == before
