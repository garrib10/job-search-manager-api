import os
from collections.abc import Generator
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.database import Base, get_db
from app.main import app
from app.models import Company, Interview, JobApplication, User

load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL is not configured"
    )


test_engine = create_engine(
    TEST_DATABASE_URL,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database() -> Generator[None, None, None]:
    """
    Create the test database tables before the test session begins
    and remove them when the full test session is finished.

    WHY:
    Tests should run against an isolated database schema rather than
    using the development database.
    """
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    yield

    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def clean_database() -> Generator[None, None, None]:
    """
    Remove test data after every individual test.

    WHY:
    Each test should start with predictable database state and should
    not depend on records created by another test.

    Child tables are cleared before parent tables so foreign key
    constraints are respected.
    """
    yield

    with test_engine.begin() as connection:
        connection.execute(Interview.__table__.delete())
        connection.execute(JobApplication.__table__.delete())
        connection.execute(Company.__table__.delete())
        connection.execute(User.__table__.delete())

@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """
    Provide a SQLAlchemy database session for an individual test.

    WHY:
    Tests need their own database session so they do not reuse the
    application's normal development database session.
    """
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.rollback()
        db.close()

@pytest.fixture
def client(
    db_session: Session,
) -> Generator[TestClient, None, None]:
    """
    Provide a FastAPI TestClient that uses the test database.

    WHY:
    FastAPI dependency overrides let the existing API endpoints use
    the testing session without changing application code.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
