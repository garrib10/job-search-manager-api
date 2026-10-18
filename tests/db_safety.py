"""
Guards that stop the test suite from running destructive operations against a
database that is not clearly a disposable test database.

WHY:
tests/conftest.py drops and recreates every table, and deletes all rows after
each test. If TEST_DATABASE_URL pointed at a development or production database
by mistake, the suite would wipe it. These checks run on the URL of the actual
test engine before anything destructive happens.

Error messages name the database but never include the URL, so credentials are
not exposed.
"""

from sqlalchemy import Engine, MetaData
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


class UnsafeTestDatabaseError(RuntimeError):
    """Raised when the configured test database is missing or unsafe to reset."""


def parse_test_database_url(raw_url: str | None) -> URL:
    """Parse TEST_DATABASE_URL without ever echoing its contents."""
    if not raw_url:
        raise UnsafeTestDatabaseError("TEST_DATABASE_URL is not configured.")

    try:
        return make_url(raw_url)
    except ArgumentError:
        # `from None` drops SQLAlchemy's error, which repeats the full URL.
        raise UnsafeTestDatabaseError("TEST_DATABASE_URL is not a valid database URL.") from None


def assert_safe_test_database(url: URL, app_database_name: str) -> None:
    """
    Refuse to continue unless the database name contains "test" and differs
    from the application's DB_NAME.
    """
    database_name = url.database

    if not database_name:
        raise UnsafeTestDatabaseError("TEST_DATABASE_URL does not name a database.")

    if "test" not in database_name.lower():
        raise UnsafeTestDatabaseError(
            f"Refusing to reset database {database_name!r}: a test database name must contain 'test'."
        )

    if database_name.lower() == app_database_name.lower():
        raise UnsafeTestDatabaseError(
            f"Refusing to reset database {database_name!r}: it is the application database (DB_NAME)."
        )


def reset_test_schema(engine: Engine, metadata: MetaData, app_database_name: str) -> None:
    """Drop and recreate every table, but only after the safety checks pass."""
    assert_safe_test_database(engine.url, app_database_name)

    metadata.drop_all(bind=engine)
    metadata.create_all(bind=engine)


def drop_test_schema(engine: Engine, metadata: MetaData, app_database_name: str) -> None:
    """Drop every table, but only after the safety checks pass."""
    assert_safe_test_database(engine.url, app_database_name)

    metadata.drop_all(bind=engine)
