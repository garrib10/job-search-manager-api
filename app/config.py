import logging
from functools import lru_cache
from typing import Literal
from urllib.parse import quote_plus

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# WHY:
# RFC 7518 (section 3.2) requires an HMAC key at least as long as the hash
# output: 256 bits for HS256, 384 for HS384, 512 for HS512.
MIN_HMAC_BYTES = {
    "HS256": 32,
    "HS384": 48,
    "HS512": 64,
}

# Values that appear in this repository (.env.example, CI) and must never be
# used as the production signing secret.
KNOWN_PLACEHOLDER_SECRETS = frozenset(
    {
        "your_secure_random_secret_here",
        "ci-only-jwt-secret-not-used-outside-github-actions",
    }
)

MAX_PRODUCTION_TOKEN_MINUTES = 24 * 60

# Shown in error messages. Named without "secret"/"key" because scanners
# treat such names as sensitive; this is only a shell command.
GENERATION_COMMAND = 'python -c "import secrets; print(secrets.token_urlsafe(48))"'


class SettingsError(RuntimeError):
    """
    Raised when configuration is missing, invalid, or unsafe for production.

    WHY:
    Messages name the environment variable and the problem but never include
    the configured values, so secrets don't end up in deployment logs.
    """


class Settings(BaseSettings):
    """
    Central application configuration.

    Values are loaded from environment variables so local development
    and production can use different settings without changing code.
    """

    app_name: str = "Job Search Manager API"
    app_version: str = "0.1.0"
    app_env: str = "development"

    db_host: str
    db_port: int = 3306
    db_name: str
    db_user: str
    db_password: str = Field(repr=False)

    # ------------------------------------------------------------------
    # JWT Authentication Settings
    #
    # WHY:
    # These settings control how JSON Web Tokens are signed and how
    # long authenticated sessions remain valid. Only HMAC algorithms are
    # accepted: the app signs with a shared secret, so "none" or an
    # asymmetric algorithm would be a misconfiguration.
    # ------------------------------------------------------------------

    jwt_secret_key: str = Field(repr=False)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def database_url(self) -> str:
        """
        Build the SQLAlchemy connection URL from environment variables.

        quote_plus safely encodes special characters in the password.
        """
        encoded_password = quote_plus(self.db_password)

        return (
            f"mysql+pymysql://{self.db_user}:{encoded_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


def find_unsafe_settings(settings: Settings) -> list[tuple[str, str]]:
    """
    List every setting that would be unsafe in production.

    Returns (variable name, explanation) pairs. Explanations say what to change
    without including anything derived from a secret, not even its length.
    """
    problems = []
    required_bytes = MIN_HMAC_BYTES[settings.jwt_algorithm]

    if len(settings.jwt_secret_key.encode("utf-8")) < required_bytes:
        problems.append((
            "JWT_SECRET_KEY",
            f"shorter than the {required_bytes} bytes {settings.jwt_algorithm} requires. "
            f"Generate one with: {GENERATION_COMMAND}",
        ))

    if settings.jwt_secret_key in KNOWN_PLACEHOLDER_SECRETS:
        problems.append((
            "JWT_SECRET_KEY",
            f"a placeholder from this repository. Generate one with: {GENERATION_COMMAND}",
        ))

    if not settings.db_password:
        problems.append(("DB_PASSWORD", "empty."))

    if not 1 <= settings.access_token_expire_minutes <= MAX_PRODUCTION_TOKEN_MINUTES:
        problems.append((
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            f"not between 1 and {MAX_PRODUCTION_TOKEN_MINUTES} (24 hours); "
            f"it is {settings.access_token_expire_minutes}.",
        ))

    return problems


def check_settings(settings: Settings) -> None:
    """
    Refuse to run in production with unsafe settings; warn about them elsewhere.

    WHY:
    A short or placeholder signing secret lets anyone forge login tokens. In
    production that must stop the app (and migrations) from starting, with a
    full explanation in the error. In development and tests the app keeps
    running and only the variable names are logged, so nothing about the
    secrets reaches the logs.
    """
    problems = find_unsafe_settings(settings)

    if not problems:
        return

    if settings.is_production:
        details = "\n".join(f"- {name} is {explanation}" for name, explanation in problems)
        raise SettingsError(f"Refusing to start with APP_ENV=production because of unsafe settings:\n{details}")

    names = ", ".join(sorted({name for name, _ in problems}))
    logger.warning("These settings would be refused in production: %s", names)


def load_settings() -> Settings:
    """
    Load and check settings, reporting problems without exposing values.

    WHY:
    Pydantic's validation errors include the submitted input, which can
    contain the database password or signing secret. Only the variable names
    and error messages are reported here.
    """
    try:
        settings = Settings()
    except ValidationError as error:
        details = "\n".join(
            f"- {'.'.join(str(part) for part in issue['loc']).upper()}: {issue['msg']}"
            for issue in error.errors(include_input=False, include_url=False)
        )
        raise SettingsError(f"Invalid configuration:\n{details}") from None

    check_settings(settings)

    return settings


@lru_cache
def get_settings() -> Settings:
    """Create, check, and reuse one Settings object."""
    return load_settings()
