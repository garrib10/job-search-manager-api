"""
New companies and applications are owned by the authenticated user.

WHY:
user_id is NOT NULL, so create endpoints must fill it in. The owner always
comes from the bearer token; a user_id in the request body is ignored.
Cross-user isolation of reads, updates, and deletes is covered in
tests/test_isolation.py.
"""

from sqlalchemy import select

from app.models import Company, JobApplication, User
from tests.conftest import TEST_USER_EMAIL


def current_user_id(db_session) -> int:
    return db_session.scalar(select(User.id).where(User.email == TEST_USER_EMAIL))


def test_new_company_is_owned_by_authenticated_user(client, auth_headers, db_session):
    response = client.post(
        "/companies",
        json={"name": "Acme", "user_id": 999999},
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert "user_id" not in response.json()

    company = db_session.get(Company, response.json()["id"])

    assert company.user_id == current_user_id(db_session)


def test_new_application_is_owned_by_authenticated_user(client, auth_headers, db_session):
    company = client.post("/companies", json={"name": "Acme"}, headers=auth_headers).json()

    response = client.post(
        "/applications",
        json={
            "job_title": "Backend Engineer",
            "company_id": company["id"],
            "job_url": "https://example.com/jobs/owned",
            "user_id": 999999,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert "user_id" not in response.json()

    application = db_session.get(JobApplication, response.json()["id"])

    assert application.user_id == current_user_id(db_session)
