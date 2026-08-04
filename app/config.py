from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration.

    Environment variables keep deployment-specific values outside the
    source code. Railway can provide the same variables in production.
    """

    app_name: str = "Job Search Manager API"
    app_version: str = "0.1.0"
    app_env: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Create the settings object once and reuse it.

    Configuration does not need to be reread for every HTTP request.
    """
    return Settings()