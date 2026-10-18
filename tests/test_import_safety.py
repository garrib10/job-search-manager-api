"""
Importing the application must not connect to a database or run SQL.

WHY:
The schema used to be created by Base.metadata.create_all() at import time,
which meant importing app.main (in tests, tools, or the server) wrote to
whatever database DB_* pointed at. Schema changes now happen only through
explicit Alembic migrations.

The import runs in a fresh Python process so app.main is imported for the
first time. DB_HOST points at an unresolvable host, so any connection attempt
would fail the import; SQLAlchemy event listeners also record any connection
or statement that does happen.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

IMPORT_CHECK = """
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

events = []
event.listen(Pool, "connect", lambda *args: events.append("connect"))
event.listen(Engine, "before_cursor_execute", lambda *args: events.append("execute"))

import app.main  # noqa: E402,F401

print("DATABASE_EVENTS=" + ",".join(events))
"""


def test_importing_app_does_not_touch_the_database():
    env = {
        **os.environ,
        "DB_HOST": "db.invalid",
        "DB_PORT": "3306",
        "DB_NAME": "import_safety_check",
        "DB_USER": "import_safety_check",
        "DB_PASSWORD": "import_safety_check",
        "JWT_SECRET_KEY": "import-safety-check",
    }

    result = subprocess.run(
        [sys.executable, "-c", IMPORT_CHECK],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr

    reported = [line for line in result.stdout.splitlines() if line.startswith("DATABASE_EVENTS=")]

    assert reported == ["DATABASE_EVENTS="], reported
