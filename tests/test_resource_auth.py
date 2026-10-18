"""
Authentication regression tests for company, application, and interview routes.

WHY:
Every resource endpoint requires a valid bearer token. These tests use the
plain (unauthenticated) `client` fixture and only send a token when a test
needs one, so a route that loses its protection fails here.

These tests only cover authentication. Isolation between authenticated users
is covered in tests/test_isolation.py.
"""

from datetime import timedelta

import pytest

from app.security import create_access_token
from tests.conftest import TEST_USER_EMAIL

COMPANY_BODY = {"name": "Acme"}
APPLICATION_BODY = {
    "job_title": "Backend Engineer",
    "company_id": 1,
    "job_url": "https://example.com/jobs/backend-engineer",
}
INTERVIEW_BODY = {
    "application_id": 1,
    "interview_type": "technical",
    "scheduled_at": "2026-11-02T15:00:00Z",
}

# (HTTP method, route template, concrete path, request body)
RESOURCE_ENDPOINTS = [
    ("POST", "/companies", "/companies", COMPANY_BODY),
    ("GET", "/companies", "/companies", None),
    ("GET", "/companies/{company_id}", "/companies/1", None),
    ("PUT", "/companies/{company_id}", "/companies/1", COMPANY_BODY),
    ("DELETE", "/companies/{company_id}", "/companies/1", None),
    ("POST", "/applications", "/applications", APPLICATION_BODY),
    ("GET", "/applications", "/applications", None),
    ("GET", "/applications/{application_id}", "/applications/1", None),
    ("PUT", "/applications/{application_id}", "/applications/1", APPLICATION_BODY),
    ("DELETE", "/applications/{application_id}", "/applications/1", None),
    ("POST", "/interviews", "/interviews", INTERVIEW_BODY),
    ("GET", "/interviews", "/interviews", None),
    ("GET", "/interviews/{interview_id}", "/interviews/1", None),
    ("PUT", "/interviews/{interview_id}", "/interviews/1", INTERVIEW_BODY),
    ("DELETE", "/interviews/{interview_id}", "/interviews/1", None),
]

ENDPOINT_IDS = [f"{method} {template}" for method, template, _, _ in RESOURCE_ENDPOINTS]

RESOURCE_PREFIXES = ("/companies", "/applications", "/interviews")


def send(client, method, path, body, headers=None):
    return client.request(method, path, json=body, headers=headers)


def test_every_resource_route_is_covered(client):
    """
    Fail if a resource endpoint is added without being listed above.

    WHY:
    Routes are read from the OpenAPI schema rather than `app.routes`, because
    FastAPI keeps included routers as internal objects there.
    """
    paths = client.get("/openapi.json").json()["paths"]
    documented = {
        (method.upper(), path)
        for path, operations in paths.items()
        if path.startswith(RESOURCE_PREFIXES)
        for method in operations
    }
    covered = {(method, template) for method, template, _, _ in RESOURCE_ENDPOINTS}

    assert documented == covered


@pytest.mark.parametrize(("method", "template", "path", "body"), RESOURCE_ENDPOINTS, ids=ENDPOINT_IDS)
def test_resource_endpoint_requires_token(client, method, template, path, body):
    response = send(client, method, path, body)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(("method", "template", "path", "body"), RESOURCE_ENDPOINTS, ids=ENDPOINT_IDS)
def test_resource_endpoint_rejects_invalid_token(client, method, template, path, body):
    response = send(client, method, path, body, headers={"Authorization": "Bearer not-a-valid-token"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired authentication token"}


@pytest.mark.parametrize(("method", "template", "path", "body"), RESOURCE_ENDPOINTS, ids=ENDPOINT_IDS)
def test_resource_endpoint_rejects_expired_token(client, auth_headers, method, template, path, body):
    expired_token = create_access_token(TEST_USER_EMAIL, expires_delta=timedelta(minutes=-1))

    response = send(client, method, path, body, headers={"Authorization": f"Bearer {expired_token}"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired authentication token"}


def test_authenticated_request_succeeds(client, auth_headers):
    created = client.post("/companies", json=COMPANY_BODY, headers=auth_headers)

    assert created.status_code == 201

    listed = client.get("/companies", headers=auth_headers)

    assert listed.status_code == 200
    assert [company["name"] for company in listed.json()] == ["Acme"]


def test_rejected_writes_do_not_change_data(client, auth_headers):
    company = client.post("/companies", json={"name": "Original"}, headers=auth_headers).json()
    application = client.post(
        "/applications",
        json={**APPLICATION_BODY, "company_id": company["id"]},
        headers=auth_headers,
    ).json()
    interview = client.post(
        "/interviews",
        json={**INTERVIEW_BODY, "application_id": application["id"]},
        headers=auth_headers,
    ).json()

    unauthenticated_writes = [
        ("POST", "/companies", {"name": "Intruder"}),
        ("PUT", f"/companies/{company['id']}", {"name": "Changed"}),
        ("DELETE", f"/companies/{company['id']}", None),
        ("POST", "/applications", {**APPLICATION_BODY, "company_id": company["id"], "job_url": "https://example.com/jobs/other"}),
        ("PUT", f"/applications/{application['id']}", {**APPLICATION_BODY, "company_id": company["id"], "job_title": "Changed"}),
        ("DELETE", f"/applications/{application['id']}", None),
        ("POST", "/interviews", {**INTERVIEW_BODY, "application_id": application["id"], "scheduled_at": "2026-11-03T15:00:00Z"}),
        ("PUT", f"/interviews/{interview['id']}", {**INTERVIEW_BODY, "application_id": application["id"], "interviewer": "Changed"}),
        ("DELETE", f"/interviews/{interview['id']}", None),
    ]

    for method, path, body in unauthenticated_writes:
        assert send(client, method, path, body).status_code == 401, f"{method} {path}"

    companies = client.get("/companies", headers=auth_headers).json()
    applications = client.get("/applications", headers=auth_headers).json()
    interviews = client.get("/interviews", headers=auth_headers).json()

    assert companies == [company]
    assert applications == [application]
    assert interviews == [interview]


def test_public_endpoints_do_not_require_token(client):
    credentials = {"email": "public-check@example.com", "password": "TestPassword123!"}

    assert client.get("/health").status_code == 200
    assert client.post("/auth/register", json=credentials).status_code == 201
    assert client.post("/auth/login", json=credentials).status_code == 200
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


def test_auth_me_still_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_openapi_marks_resource_endpoints_as_secured(client):
    paths = client.get("/openapi.json").json()["paths"]

    for method, template, _, _ in RESOURCE_ENDPOINTS:
        operation = paths[template][method.lower()]

        assert operation.get("security") == [{"HTTPBearer": []}], f"{method} {template}"

    assert "security" not in paths["/health"]["get"]
    assert "security" not in paths["/auth/register"]["post"]
    assert "security" not in paths["/auth/login"]["post"]
    assert paths["/auth/me"]["get"].get("security") == [{"HTTPBearer": []}]
