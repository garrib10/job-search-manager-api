"""
Delete rules, per-user job URL uniqueness, and database conflict handling.

WHY:
- Deleting a company that still has applications is refused (409) so job
  history is never deleted by accident.
- Deleting an application deletes its interviews.
- A job URL is unique per user, not globally.
- If a request slips past the service checks (two concurrent requests, for
  example) and hits a database constraint, the client gets a generic 409, the
  details are logged server-side only, and the session is rolled back so the
  next request works. The test client shares one session across requests, so a
  missing rollback would make the follow-up request fail.
"""

import logging

from app.handlers.exception_handlers import INTEGRITY_ERROR_DETAIL
from app.models import Interview, JobApplication
from app.services import application_service, company_service


def create_company(client, headers, name="Acme"):
    return client.post("/companies", json={"name": name}, headers=headers).json()


def create_application(client, headers, company_id, url="https://example.com/jobs/1"):
    response = client.post(
        "/applications",
        json={"job_title": "Engineer", "company_id": company_id, "job_url": url},
        headers=headers,
    )
    return response


def create_interview(client, headers, application_id, when="2026-11-02T15:00:00Z"):
    return client.post(
        "/interviews",
        json={"application_id": application_id, "interview_type": "technical", "scheduled_at": when},
        headers=headers,
    ).json()


def test_deleting_company_with_applications_is_refused(client, auth_headers):
    company = create_company(client, auth_headers)
    application = create_application(client, auth_headers, company["id"]).json()

    response = client.delete(f"/companies/{company['id']}", headers=auth_headers)

    assert response.status_code == 409
    assert response.json() == {"detail": "Company has job applications. Delete or move them first."}
    assert client.get(f"/companies/{company['id']}", headers=auth_headers).status_code == 200
    assert client.get(f"/applications/{application['id']}", headers=auth_headers).status_code == 200


def test_deleting_company_without_applications_succeeds(client, auth_headers):
    company = create_company(client, auth_headers)

    assert client.delete(f"/companies/{company['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/companies/{company['id']}", headers=auth_headers).status_code == 404


def test_company_can_be_deleted_after_its_applications(client, auth_headers):
    company = create_company(client, auth_headers)
    application = create_application(client, auth_headers, company["id"]).json()

    assert client.delete(f"/applications/{application['id']}", headers=auth_headers).status_code == 204
    assert client.delete(f"/companies/{company['id']}", headers=auth_headers).status_code == 204


def test_deleting_application_deletes_its_interviews(client, auth_headers, db_session):
    company = create_company(client, auth_headers)
    application = create_application(client, auth_headers, company["id"]).json()
    other = create_application(client, auth_headers, company["id"], url="https://example.com/jobs/2").json()
    first = create_interview(client, auth_headers, application["id"])
    second = create_interview(client, auth_headers, application["id"], when="2026-11-03T15:00:00Z")
    kept = create_interview(client, auth_headers, other["id"])

    response = client.delete(f"/applications/{application['id']}", headers=auth_headers)

    assert response.status_code == 204
    for interview in (first, second):
        assert client.get(f"/interviews/{interview['id']}", headers=auth_headers).status_code == 404
    assert [item["id"] for item in client.get("/interviews", headers=auth_headers).json()] == [kept["id"]]

    db_session.expire_all()
    assert db_session.get(Interview, first["id"]) is None
    assert db_session.get(Interview, kept["id"]) is not None


def test_same_user_cannot_track_a_job_url_twice(client, auth_headers):
    company = create_company(client, auth_headers)
    assert create_application(client, auth_headers, company["id"]).status_code == 201

    duplicate = create_application(client, auth_headers, company["id"])

    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "An application with this job URL already exists"}


def test_different_users_can_track_the_same_job_url(client, auth_headers, other_auth_headers):
    a_company = create_company(client, auth_headers)
    b_company = create_company(client, other_auth_headers)

    assert create_application(client, auth_headers, a_company["id"]).status_code == 201
    assert create_application(client, other_auth_headers, b_company["id"]).status_code == 201


def test_update_to_own_duplicate_job_url_is_refused(client, auth_headers):
    company = create_company(client, auth_headers)
    create_application(client, auth_headers, company["id"], url="https://example.com/jobs/1")
    second = create_application(client, auth_headers, company["id"], url="https://example.com/jobs/2").json()

    response = client.put(
        f"/applications/{second['id']}",
        json={"job_title": "Engineer", "company_id": company["id"], "job_url": "https://example.com/jobs/1"},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert client.get(f"/applications/{second['id']}", headers=auth_headers).json()["job_url"] == (
        "https://example.com/jobs/2"
    )


def test_database_conflict_returns_generic_409_and_rolls_back(client, auth_headers, db_session, monkeypatch, caplog):
    company = create_company(client, auth_headers)
    create_application(client, auth_headers, company["id"])

    # Simulate a concurrent request that passed the duplicate check before the
    # first insert committed: the service check finds nothing, so the insert
    # reaches the database's unique constraint.
    monkeypatch.setattr(application_service, "get_application_by_job_url", lambda *args, **kwargs: None)

    with caplog.at_level(logging.WARNING, logger="app.handlers.exception_handlers"):
        response = create_application(client, auth_headers, company["id"])

    assert response.status_code == 409
    assert response.json() == {"detail": INTEGRITY_ERROR_DETAIL}
    for leaked in ("Duplicate", "uq_job_applications", "job_applications", "INSERT", "example.com"):
        assert leaked not in response.text

    assert "Database integrity error on POST /applications" in caplog.text
    assert "Duplicate entry" in caplog.text

    follow_up = create_application(client, auth_headers, company["id"], url="https://example.com/jobs/after")
    assert follow_up.status_code == 201

    db_session.expire_all()
    assert db_session.query(JobApplication).count() == 2


def test_database_blocks_company_delete_even_if_check_is_bypassed(client, auth_headers, monkeypatch):
    company = create_company(client, auth_headers)
    create_application(client, auth_headers, company["id"])

    monkeypatch.setattr(company_service, "company_has_applications", lambda *args, **kwargs: False)

    response = client.delete(f"/companies/{company['id']}", headers=auth_headers)

    assert response.status_code == 409
    assert response.json() == {"detail": INTEGRITY_ERROR_DETAIL}
    assert client.get(f"/companies/{company['id']}", headers=auth_headers).status_code == 200
    assert len(client.get("/applications", headers=auth_headers).json()) == 1
