import os
from collections.abc import Generator
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import Company, Interview, JobApplication, User
from app.schemas import UserCreate
from app.security import create_access_token
from app.services import auth_service
from tests.db_safety import (
    assert_safe_test_database,
    drop_test_schema,
    parse_test_database_url,
    reset_test_schema,
)

load_dotenv()

TEST_DATABASE_URL = parse_test_database_url(
    os.getenv("TEST_DATABASE_URL")
)

APP_DATABASE_NAME = get_settings().db_name

# WHY:
# Fail before any fixture runs if the test database is not clearly disposable.
# The check uses the URL of the engine the fixtures actually use.
test_engine = create_engine(
    TEST_DATABASE_URL,
)

assert_safe_test_database(test_engine.url, APP_DATABASE_NAME)

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
    using the development database. Tables are created from the models
    here; migrations are verified separately (see the CI workflow).
    """
    reset_test_schema(test_engine, Base.metadata, APP_DATABASE_NAME)

    yield

    drop_test_schema(test_engine, Base.metadata, APP_DATABASE_NAME)


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


TEST_USER_EMAIL = "resource-user@example.com"
TEST_USER_PASSWORD = "TestPassword123!"


@pytest.fixture
def auth_headers(
    db_session: Session,
) -> dict[str, str]:
    """
    Create a test user and return a valid bearer token header for it.

    WHY:
    Company, application, and interview endpoints require login. The user
    is created through the same service and token function the API uses,
    so tests exercise the real authentication path.
    """
    auth_service.register_user(
        db_session,
        UserCreate(
            email=TEST_USER_EMAIL,
            password=TEST_USER_PASSWORD,
        ),
    )

    token = create_access_token(TEST_USER_EMAIL)

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def authenticated_client(
    client: TestClient,
    auth_headers: dict[str, str],
) -> TestClient:
    """
    Send the test user's bearer token with every request made by `client`.

    WHY:
    Resource test modules opt in with
    `pytestmark = pytest.mark.usefixtures("authenticated_client")`, so their
    existing tests keep using `client` while authenticated.
    """
    client.headers.update(auth_headers)

    return client
