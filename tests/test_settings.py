"""
Production settings guard (app/config.py).

WHY:
In production, a short or placeholder JWT signing secret would let anyone
forge login tokens, so the app must refuse to start. Development and test keep
working with a warning. Error messages must never contain the secret or the
database password.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app.config import (
    MIN_JWT_SECRET_BYTES,
    Settings,
    SettingsError,
    check_settings,
    load_settings,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

STRONG_SECRET = "s" * 48
WEAK_SECRET = "weak-secret-value-123"
DB_PASSWORD = "db-password-value-456"


def make_settings(**overrides) -> Settings:
    values = {
        "app_env": "production",
        "db_host": "localhost",
        "db_name": "job_search",
        "db_user": "app",
        "db_password": DB_PASSWORD,
        "jwt_secret_key": STRONG_SECRET,
        "jwt_algorithm": "HS256",
        "access_token_expire_minutes": 30,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_safe_production_settings_are_accepted():
    check_settings(make_settings())


@pytest.mark.parametrize("app_env", ["production", "Production", " PRODUCTION "])
def test_production_rejects_a_short_secret(app_env):
    with pytest.raises(SettingsError) as error:
        check_settings(make_settings(app_env=app_env, jwt_secret_key=WEAK_SECRET))

    message = str(error.value)
    assert "JWT_SECRET_KEY is 21 bytes; HS256 needs at least 32" in message
    assert "secrets.token_urlsafe" in message
    assert WEAK_SECRET not in message


@pytest.mark.parametrize(("algorithm", "required"), sorted(MIN_JWT_SECRET_BYTES.items()))
def test_minimum_secret_length_follows_the_algorithm(algorithm, required):
    check_settings(make_settings(jwt_algorithm=algorithm, jwt_secret_key="k" * required))

    with pytest.raises(SettingsError, match=f"needs at least {required}"):
        check_settings(make_settings(jwt_algorithm=algorithm, jwt_secret_key="k" * (required - 1)))


def test_secret_length_is_measured_in_bytes():
    # 16 two-byte characters are 32 bytes, enough for HS256.
    check_settings(make_settings(jwt_secret_key="é" * 16))


@pytest.mark.parametrize(
    "placeholder",
    ["your_secure_random_secret_here", "ci-only-jwt-secret-not-used-outside-github-actions"],
)
def test_production_rejects_repository_placeholders(placeholder):
    with pytest.raises(SettingsError, match="placeholder"):
        check_settings(make_settings(jwt_secret_key=placeholder))


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"db_password": ""}, "DB_PASSWORD is empty"),
        ({"access_token_expire_minutes": 0}, "ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and 1440"),
        ({"access_token_expire_minutes": 1441}, "ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and 1440"),
    ],
)
def test_production_rejects_other_unsafe_settings(overrides, message):
    with pytest.raises(SettingsError, match=message):
        check_settings(make_settings(**overrides))


def test_all_problems_are_reported_together():
    with pytest.raises(SettingsError) as error:
        check_settings(make_settings(jwt_secret_key=WEAK_SECRET, db_password="", access_token_expire_minutes=0))

    assert str(error.value).count("\n- ") == 3


@pytest.mark.parametrize("algorithm", ["none", "RS256", "HS1"])
def test_only_hmac_algorithms_are_accepted_in_any_environment(algorithm):
    with pytest.raises(ValueError):
        make_settings(app_env="development", jwt_algorithm=algorithm)


@pytest.mark.parametrize("app_env", ["development", "test", "ci"])
def test_other_environments_warn_but_keep_running(app_env, caplog):
    with caplog.at_level(logging.WARNING, logger="app.config"):
        check_settings(make_settings(app_env=app_env, jwt_secret_key=WEAK_SECRET))

    assert "would be refused in production" in caplog.text
    assert WEAK_SECRET not in caplog.text


def test_invalid_configuration_is_reported_without_values(monkeypatch):
    monkeypatch.chdir(REPO_ROOT / "tests")  # no .env file here
    for name in ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD", "JWT_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DB_PASSWORD", DB_PASSWORD)
    monkeypatch.setenv("JWT_SECRET_KEY", STRONG_SECRET)
    monkeypatch.setenv("DB_PORT", "not-a-port")

    with pytest.raises(SettingsError) as error:
        load_settings()

    message = str(error.value)
    assert "DB_HOST: Field required" in message
    assert "DB_PORT:" in message
    assert DB_PASSWORD not in message
    assert STRONG_SECRET not in message


def test_settings_repr_hides_secrets():
    shown = repr(make_settings())

    assert STRONG_SECRET not in shown
    assert DB_PASSWORD not in shown


def run_app_import(**env_overrides) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "DB_HOST": "localhost",
        "DB_NAME": "startup_check",
        "DB_USER": "startup_check",
        "DB_PASSWORD": DB_PASSWORD,
        "JWT_ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
        **env_overrides,
    }
    return subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_production_startup_fails_with_unsafe_settings():
    result = run_app_import(APP_ENV="production", JWT_SECRET_KEY=WEAK_SECRET)

    assert result.returncode != 0
    assert "Refusing to start with APP_ENV=production" in result.stderr
    assert WEAK_SECRET not in result.stderr
    assert DB_PASSWORD not in result.stderr


def test_production_startup_succeeds_with_safe_settings():
    result = run_app_import(APP_ENV="production", JWT_SECRET_KEY=STRONG_SECRET)

    assert result.returncode == 0, result.stderr
