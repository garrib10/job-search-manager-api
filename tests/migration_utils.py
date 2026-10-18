"""
Helpers for tests that run real Alembic migrations against the disposable
test database (guarded by tests/db_safety.py).
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from tests.conftest import test_engine

REPO_ROOT = Path(__file__).resolve().parents[1]


def alembic_config(owner_email: str | None = None) -> Config:
    config = Config()
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    config.cmd_opts = type("Options", (), {"x": [f"owner_email={owner_email}"] if owner_email else []})()
    return config


HEAD = ScriptDirectory.from_config(alembic_config()).get_current_head()


def alembic(action: str, revision: str, owner_email: str | None = None) -> None:
    """Run an Alembic command against the test database, like the CLI would."""
    config = alembic_config(owner_email)

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


def column_names(table: str) -> set[str]:
    return {column["name"] for column in inspect(test_engine).get_columns(table)}
