from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    db_password: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

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


@lru_cache
def get_settings() -> Settings:
    """Create and reuse one Settings object."""
    return Settings()