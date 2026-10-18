"""
Tests for the test-database guard in tests/db_safety.py.

These never connect to a database: engines created with create_engine() do not
connect until used, and the metadata passed to the reset helpers is a mock, so
an unsafe target is rejected without touching anything.
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from tests.conftest import APP_DATABASE_NAME, test_engine
from tests.db_safety import (
    UnsafeTestDatabaseError,
    assert_safe_test_database,
    drop_test_schema,
    parse_test_database_url,
    reset_test_schema,
)

APP_DB = "job_search"


def url(database: str) -> str:
    return f"mysql+pymysql://user:s3cret-pass@localhost:3306/{database}"


def test_configured_test_engine_passes_guard():
    assert_safe_test_database(test_engine.url, APP_DATABASE_NAME)


@pytest.mark.parametrize("database", ["job_search_test", "TEST_db", "testing"])
def test_safe_test_database_is_accepted(database):
    assert_safe_test_database(make_url(url(database)), APP_DB)


@pytest.mark.parametrize(
    ("database", "app_db", "reason"),
    [
        ("job_search", "job_search", "must contain 'test'"),
        ("production", "job_search", "must contain 'test'"),
        ("job_search_test", "job_search_test", "application database"),
        ("Job_Search_Test", "job_search_test", "application database"),
    ],
)
def test_unsafe_test_database_is_rejected(database, app_db, reason):
    with pytest.raises(UnsafeTestDatabaseError, match=reason):
        assert_safe_test_database(make_url(url(database)), app_db)


def test_url_without_database_is_rejected():
    with pytest.raises(UnsafeTestDatabaseError, match="does not name a database"):
        assert_safe_test_database(make_url("mysql+pymysql://user:s3cret-pass@localhost:3306"), APP_DB)


@pytest.mark.parametrize("raw", [None, ""])
def test_missing_test_database_url_is_rejected(raw):
    with pytest.raises(UnsafeTestDatabaseError, match="not configured"):
        parse_test_database_url(raw)


def test_invalid_test_database_url_is_rejected_without_leaking_it():
    raw = "not a url with s3cret-pass inside"

    with pytest.raises(UnsafeTestDatabaseError) as error:
        parse_test_database_url(raw)

    assert "s3cret-pass" not in str(error.value)
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__ is True


def test_rejection_message_does_not_include_password():
    with pytest.raises(UnsafeTestDatabaseError) as error:
        assert_safe_test_database(make_url(url("production")), APP_DB)

    assert "s3cret-pass" not in str(error.value)


@pytest.mark.parametrize("helper", [reset_test_schema, drop_test_schema])
def test_unsafe_target_is_rejected_before_any_destructive_operation(helper):
    engine = create_engine(url("production"))
    metadata = MagicMock()

    with pytest.raises(UnsafeTestDatabaseError):
        helper(engine, metadata, APP_DB)

    metadata.drop_all.assert_not_called()
    metadata.create_all.assert_not_called()


def test_reset_runs_only_after_guard_passes():
    engine = create_engine(url("job_search_test"))
    metadata = MagicMock()

    reset_test_schema(engine, metadata, APP_DB)

    metadata.drop_all.assert_called_once_with(bind=engine)
    metadata.create_all.assert_called_once_with(bind=engine)
