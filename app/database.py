from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


settings = get_settings()


engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    WHY:
    Every database model will inherit from this class so SQLAlchemy
    can track the model and map it to a database table.
    """

    pass


def get_db() -> Generator[Session, None, None]:
    """
    Provide one SQLAlchemy database session per request.

    WHY:
    Each request should use its own session, and the session must be
    closed afterward so database connections are returned to the pool.
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()