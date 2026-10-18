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
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def commit_or_rollback(db: Session) -> None:
    """
    Commit the session, rolling it back if the database rejects the changes.

    WHY:
    If a commit fails (for example, a unique or foreign key constraint is
    violated by a concurrent request), the session must be rolled back
    before it can be used again, and nothing from the failed request may be
    left pending. The error is re-raised so the global IntegrityError
    handler can return a 409.
    """
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise