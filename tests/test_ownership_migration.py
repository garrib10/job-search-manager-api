"""
Tests for the two-stage ownership migration (865d60d22f27, add88b8a484a).

WHY:
Existing databases have companies and applications with no owner. These tests
run the real migrations against the disposable test database (guarded by
tests/db_safety.py) with representative pre-existing data, and check that
owners are assigned only when explicitly chosen, that bad input stops the
migration before anything changes, and that data and relationships survive.

Each test starts from an empty database and, afterwards, restores the tables
the rest of the suite expects.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.database import Base
from tests.conftest import APP_DATABASE_NAME, test_engine
from tests.db_safety import drop_all_tables, reset_test_schema

REPO_ROOT = Path(__file__).resolve().parents[1]

BASELINE = "2bf55ef584f4"
STAGE_1 = "865d60d22f27"
HEAD = "add88b8a484a"

OWNER_EMAIL = "owner@example.com"
OTHER_EMAIL = "other@example.com"


@pytest.fixture
def empty_database():
    drop_all_tables(test_engine, APP_DATABASE_NAME)

    yield

    drop_all_tables(test_engine, APP_DATABASE_NAME)
    reset_test_schema(test_engine, Base.metadata, APP_DATABASE_NAME)


def alembic(action: str, revision: str, owner_email: str | None = None) -> None:
    """Run an Alembic command against the test database, like the CLI would."""
    config = Config()
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    config.cmd_opts = type("Options", (), {"x": [f"owner_email={owner_email}"] if owner_email else []})()

    with test_engine.connect() as connection:
        config.attributes["connection"] = connection
        getattr(command, action)(config, revision)
        connection.commit()


def query(sql: str, **params):
    with test_engine.connect() as connection:
        return connection.execute(text(sql), params).all()


def scalar(sql: str, **params):
    return query(sql, **params)[0][0]


def execute(sql: str, **params) -> None:
    with test_engine.begin() as connection:
        connection.execute(text(sql), params)


def current_revision() -> str | None:
    with test_engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def user_id_nullable(table: str) -> bool:
    columns = {column["name"]: column for column in inspect(test_engine).get_columns(table)}
    return columns["user_id"]["nullable"]


def seed_pre_ownership_data() -> dict[str, int]:
    """
    Insert data shaped like a database created before ownership existed:
    two users, two companies, three applications, two interviews.
    """
    for email, active in ((OWNER_EMAIL, 1), (OTHER_EMAIL, 1), ("inactive@example.com", 0)):
        execute(
            "INSERT INTO users (email, hashed_password, is_active) VALUES (:email, 'not-a-real-hash', :active)",
            email=email,
            active=active,
        )

    execute("INSERT INTO companies (id, name) VALUES (1, 'Acme'), (2, 'Globex')")
    execute(
        "INSERT INTO job_applications (id, job_title, job_url, status, date_saved, company_id) VALUES "
        "(10, 'Backend Engineer', 'https://example.com/1', 'applied', '2026-10-01', 1), "
        "(11, 'Platform Engineer', 'https://example.com/2', 'saved', '2026-10-02', 1), "
        "(12, 'Data Engineer', 'https://example.com/3', 'interviewing', '2026-10-03', 2)"
    )
    execute(
        "INSERT INTO interviews (id, interview_type, status, outcome, scheduled_at, application_id) VALUES "
        "(100, 'technical', 'scheduled', 'pending', '2026-11-01 15:00:00', 10), "
        "(101, 'hr', 'completed', 'advanced', '2026-10-20 10:00:00', 12)"
    )

    return {
        "owner": scalar("SELECT id FROM users WHERE email = :e", e=OWNER_EMAIL),
        "other": scalar("SELECT id FROM users WHERE email = :e", e=OTHER_EMAIL),
    }


def snapshot_relationships():
    return (
        query("SELECT id, name FROM companies ORDER BY id"),
        query("SELECT id, company_id, job_url FROM job_applications ORDER BY id"),
        query("SELECT id, application_id FROM interviews ORDER BY id"),
    )


def test_empty_database_upgrades_to_head_without_any_user(empty_database):
    alembic("upgrade", "head")

    assert current_revision() == HEAD
    assert scalar("SELECT COUNT(*) FROM users") == 0

    inspector = inspect(test_engine)
    for table in ("companies", "job_applications"):
        assert user_id_nullable(table) is False
        assert f"ix_{table}_user_id" in {index["name"] for index in inspector.get_indexes(table)}
        foreign_keys = {fk["name"]: fk for fk in inspector.get_foreign_keys(table)}
        fk = foreign_keys[f"fk_{table}_user_id_users"]
        assert (fk["constrained_columns"], fk["referred_table"], fk["referred_columns"]) == (["user_id"], "users", ["id"])

    assert "user_id" not in {column["name"] for column in inspector.get_columns("interviews")}

    with test_engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection, opts={"compare_type": True}), Base.metadata)

    assert differences == []


def test_existing_records_are_assigned_to_the_confirmed_owner(empty_database):
    alembic("upgrade", BASELINE)
    users = seed_pre_ownership_data()
    before = snapshot_relationships()

    alembic("upgrade", "head", owner_email=OWNER_EMAIL)

    assert current_revision() == HEAD
    assert query("SELECT DISTINCT user_id FROM companies") == [(users["owner"],)]
    assert query("SELECT DISTINCT user_id FROM job_applications") == [(users["owner"],)]
    assert snapshot_relationships() == before
    assert user_id_nullable("companies") is False
    assert user_id_nullable("job_applications") is False


def test_owners_assigned_before_stage_two_are_kept(empty_database):
    alembic("upgrade", BASELINE)
    users = seed_pre_ownership_data()
    alembic("upgrade", STAGE_1)
    execute("UPDATE companies SET user_id = :u WHERE id = 2", u=users["other"])
    execute("UPDATE job_applications SET user_id = :u WHERE company_id = 2", u=users["other"])

    alembic("upgrade", "head", owner_email=OWNER_EMAIL)

    assert query("SELECT id, user_id FROM companies ORDER BY id") == [(1, users["owner"]), (2, users["other"])]
    assert query("SELECT id, user_id FROM job_applications ORDER BY id") == [
        (10, users["owner"]),
        (11, users["owner"]),
        (12, users["other"]),
    ]


@pytest.mark.parametrize(
    ("owner_email", "message"),
    [
        (None, "have no owner"),
        ("nobody@example.com", "No user has the email"),
        ("inactive@example.com", "is inactive"),
    ],
)
def test_missing_or_invalid_owner_stops_before_any_change(empty_database, owner_email, message):
    alembic("upgrade", BASELINE)
    seed_pre_ownership_data()
    before = snapshot_relationships()

    with pytest.raises(RuntimeError, match=message):
        alembic("upgrade", "head", owner_email=owner_email)

    assert current_revision() == STAGE_1
    assert scalar("SELECT COUNT(*) FROM companies WHERE user_id IS NULL") == 2
    assert scalar("SELECT COUNT(*) FROM job_applications WHERE user_id IS NULL") == 3
    assert user_id_nullable("companies") is True
    assert user_id_nullable("job_applications") is True
    assert snapshot_relationships() == before


def test_application_owner_must_match_company_owner(empty_database):
    alembic("upgrade", BASELINE)
    users = seed_pre_ownership_data()
    alembic("upgrade", STAGE_1)
    execute("UPDATE companies SET user_id = :u WHERE id = 1", u=users["other"])

    with pytest.raises(RuntimeError, match=r"application IDs: 10, 11"):
        alembic("upgrade", "head", owner_email=OWNER_EMAIL)

    assert current_revision() == STAGE_1
    assert scalar("SELECT COUNT(*) FROM job_applications WHERE user_id IS NULL") == 3
    assert scalar("SELECT COUNT(*) FROM companies WHERE user_id IS NULL") == 1
    assert user_id_nullable("job_applications") is True


def test_final_schema_enforces_not_null_and_foreign_keys(empty_database):
    alembic("upgrade", "head")

    with pytest.raises(IntegrityError):
        execute("INSERT INTO companies (name, user_id) VALUES ('No owner', NULL)")

    with pytest.raises(IntegrityError):
        execute("INSERT INTO companies (name, user_id) VALUES ('Ghost owner', 999999)")


def test_downgrades_keep_companies_and_applications(empty_database):
    alembic("upgrade", BASELINE)
    users = seed_pre_ownership_data()
    alembic("upgrade", "head", owner_email=OWNER_EMAIL)
    before = snapshot_relationships()

    alembic("downgrade", STAGE_1)

    assert user_id_nullable("companies") is True
    assert query("SELECT DISTINCT user_id FROM companies") == [(users["owner"],)]

    alembic("downgrade", BASELINE)

    assert "user_id" not in {column["name"] for column in inspect(test_engine).get_columns("companies")}
    assert snapshot_relationships() == before
