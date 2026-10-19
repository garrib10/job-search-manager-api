"""
Railway deployment configuration (.railway/railway.ts) and the Python version pin.

WHY:
Railway Infrastructure as Code applies .railway/railway.ts to the project with
`railway config apply`. These tests fail if the file stops pointing at the real
application, the migration command, or a health check path that answers
without authentication, and they guard the two settings that keep an apply
safe: the partial that limits the file to the API service (so the MySQL
database can't be deleted), and unmanaged variables (so secrets never live in
the file). The Python pin is shared by Railway and CI.

The TypeScript file is read as text; evaluating it needs Node and the Railway
SDK, which `railway config plan` does.
"""

import importlib
import json
import re
import shlex
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IAC_DIR = REPO_ROOT / ".railway"
CONFIG = (IAC_DIR / "railway.ts").read_text()
CODE = re.sub(r"//.*", "", CONFIG)  # without comments

SERVICE_NAME = "job-search-manager-api"


def string_option(name: str) -> str:
    match = re.search(rf'^\s*{name}:\s*"([^"]*)"', CONFIG, re.MULTILINE)
    assert match, f"{name} not found in .railway/railway.ts"
    return match.group(1)


def test_only_the_iac_file_configures_railway():
    assert not (REPO_ROOT / "railway.json").exists()
    assert not (REPO_ROOT / "railway.toml").exists()
    assert sorted(p.name for p in IAC_DIR.glob("railway.*")) == ["railway.ts"]


def test_file_is_limited_to_the_api_service():
    assert re.search(rf'^export const partial = "{SERVICE_NAME}";$', CONFIG, re.MULTILINE)
    assert re.findall(r'service\("([^"]+)"', CODE) == [SERVICE_NAME]
    assert "mysql" not in CODE.lower()


def test_variables_stay_unmanaged():
    assert re.search(r"variables:\s*\{\s*managed:\s*false\s*\}", CONFIG)


def test_start_command_serves_the_app_on_railways_port():
    start = string_option("start")

    assert start == "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
    module_name, attribute = shlex.split(start)[1].split(":")
    assert hasattr(importlib.import_module(module_name), attribute)


def test_pre_deploy_command_runs_migrations():
    assert string_option("preDeploy") == "alembic upgrade head"
    assert re.search(r"preDeployTimeoutSeconds:\s*300\b", CONFIG)
    assert (REPO_ROOT / "alembic.ini").is_file()


def test_health_check_path_answers_without_a_token(client):
    path = string_option("healthcheck")
    response = client.get(path)

    assert path == "/health"
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_builds_with_railpack_from_main():
    assert re.search(r'builder:\s*"RAILPACK"', CONFIG)
    assert re.search(r'github\("garrib10/job-search-manager-api",\s*\{\s*branch:\s*"main"', CONFIG)


def test_sdk_is_pinned_and_kept_out_of_the_repository_root():
    package = json.loads((IAC_DIR / "package.json").read_text())

    assert re.fullmatch(r"\d+\.\d+\.\d+", package["devDependencies"]["railway"])
    assert (IAC_DIR / "package-lock.json").is_file()
    # A package.json at the root could make Railpack build this as a Node app.
    assert not (REPO_ROOT / "package.json").exists()


def test_python_version_pin_matches_the_tested_interpreter():
    pinned = (REPO_ROOT / ".python-version").read_text().strip()

    assert pinned == f"{sys.version_info.major}.{sys.version_info.minor}"
