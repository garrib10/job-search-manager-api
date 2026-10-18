"""
Railway deployment configuration (railway.json) and the Python version pin.

WHY:
Railway reads railway.json on every deploy and uses it instead of the
dashboard settings. These tests fail if the file stops pointing at the real
application, the migration command, or a health check path that actually
answers without authentication. The Python pin is shared by Railway and CI.
"""

import importlib
import json
import shlex
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((REPO_ROOT / "railway.json").read_text())
DEPLOY = CONFIG["deploy"]


def test_config_uses_railway_schema():
    assert CONFIG["$schema"] == "https://railway.com/railway.schema.json"


def test_start_command_serves_the_app_on_railways_port():
    assert DEPLOY["startCommand"] == "uvicorn app.main:app --host 0.0.0.0 --port $PORT"

    args = shlex.split(DEPLOY["startCommand"])
    module_name, attribute = args[1].split(":")
    assert hasattr(importlib.import_module(module_name), attribute)


def test_pre_deploy_command_runs_migrations():
    assert DEPLOY["preDeployCommand"] == ["alembic upgrade head"]
    assert (REPO_ROOT / "alembic.ini").is_file()


def test_health_check_path_answers_without_a_token(client):
    response = client.get(DEPLOY["healthcheckPath"])

    assert DEPLOY["healthcheckPath"] == "/health"
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_python_version_pin_matches_the_tested_interpreter():
    pinned = (REPO_ROOT / ".python-version").read_text().strip()

    assert pinned == f"{sys.version_info.major}.{sys.version_info.minor}"
