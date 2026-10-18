"""
Cross-user isolation for companies, applications, and interviews.

WHY:
Every record belongs to a user (interviews through their application). User A
creates a full set of records; user B, a separate account, must not be able to
see, change, delete, or reference any of them. Another user's record is
reported exactly like a missing one (404), so B cannot even learn which IDs
exist. Rejected requests must leave A's data untouched and must not create
anything for B.
"""

import pytest


@pytest.fixture
def user_a_records(client, auth_headers):
    """A company, application, and interview owned by user A."""
    company = client.post(
        "/companies",
        json={"name": "A Corp", "notes": "a-private-note"},
        headers=auth_headers,
    ).json()
    application = client.post(
        "/applications",
        json={
            "job_title": "A Engineer",
            "company_id": company["id"],
            "job_url": "https://example.com/jobs/a",
            "notes": "a-private-note",
        },
        headers=auth_headers,
    ).json()
    interview = client.post(
        "/interviews",
        json={
            "application_id": application["id"],
            "interview_type": "technical",
            "scheduled_at": "2026-11-02T15:00:00",
        },
        headers=auth_headers,
    ).json()

    return {"company": company, "application": application, "interview": interview}


@pytest.fixture
def user_b_records(client, other_auth_headers):
    """A company and application owned by user B, for re-pointing attempts."""
    company = client.post("/companies", json={"name": "B Corp"}, headers=other_auth_headers).json()
    application = client.post(
        "/applications",
        json={
            "job_title": "B Engineer",
            "company_id": company["id"],
            "job_url": "https://example.com/jobs/b",
        },
        headers=other_auth_headers,
    ).json()
    interview = client.post(
        "/interviews",
        json={
            "application_id": application["id"],
            "interview_type": "hr",
            "scheduled_at": "2026-11-03T15:00:00",
        },
        headers=other_auth_headers,
    ).json()

    return {"company": company, "application": application, "interview": interview}


def a_state(client, auth_headers, records):
    """Snapshot of user A's records, read as user A."""
    return (
        client.get(f"/companies/{records['company']['id']}", headers=auth_headers).json(),
        client.get(f"/applications/{records['application']['id']}", headers=auth_headers).json(),
        client.get(f"/interviews/{records['interview']['id']}", headers=auth_headers).json(),
    )


RESOURCES = ["companies", "applications", "interviews"]
SINGULAR = {"companies": "company", "applications": "application", "interviews": "interview"}


def test_owner_can_read_own_records(client, auth_headers, user_a_records):
    for resource in RESOURCES:
        record = user_a_records[SINGULAR[resource]]

        assert client.get(f"/{resource}/{record['id']}", headers=auth_headers).status_code == 200
        assert [item["id"] for item in client.get(f"/{resource}", headers=auth_headers).json()] == [record["id"]]


@pytest.mark.parametrize("resource", RESOURCES)
def test_lists_only_show_own_records(client, other_auth_headers, user_a_records, user_b_records, resource):
    listed = client.get(f"/{resource}", headers=other_auth_headers).json()

    assert [item["id"] for item in listed] == [user_b_records[SINGULAR[resource]]["id"]]


@pytest.mark.parametrize("resource", RESOURCES)
def test_cannot_read_another_users_record(client, other_auth_headers, user_a_records, resource):
    record_id = user_a_records[SINGULAR[resource]]["id"]

    response = client.get(f"/{resource}/{record_id}", headers=other_auth_headers)

    assert response.status_code == 404
    assert "a-private-note" not in response.text


def test_not_found_response_is_identical_for_other_users_and_missing_ids(client, other_auth_headers, user_a_records):
    for resource in RESOURCES:
        others = client.get(f"/{resource}/{user_a_records[SINGULAR[resource]]['id']}", headers=other_auth_headers)
        missing = client.get(f"/{resource}/999999", headers=other_auth_headers)

        assert (others.status_code, others.json()) == (missing.status_code, missing.json())


def test_cannot_update_another_users_records(client, auth_headers, other_auth_headers, user_a_records, user_b_records):
    before = a_state(client, auth_headers, user_a_records)
    a = user_a_records

    attempts = [
        ("/companies", a["company"]["id"], {"name": "Hijacked"}),
        (
            "/applications",
            a["application"]["id"],
            {
                "job_title": "Hijacked",
                "company_id": user_b_records["company"]["id"],
                "job_url": "https://example.com/jobs/hijacked",
            },
        ),
        (
            "/interviews",
            a["interview"]["id"],
            {
                "application_id": user_b_records["application"]["id"],
                "interview_type": "final",
                "scheduled_at": "2026-12-01T09:00:00",
            },
        ),
    ]

    for path, record_id, body in attempts:
        assert client.put(f"{path}/{record_id}", json=body, headers=other_auth_headers).status_code == 404

    assert a_state(client, auth_headers, user_a_records) == before


def test_cannot_delete_another_users_records(client, auth_headers, other_auth_headers, user_a_records):
    before = a_state(client, auth_headers, user_a_records)

    for resource in ("interviews", "applications", "companies"):
        record_id = user_a_records[SINGULAR[resource]]["id"]

        assert client.delete(f"/{resource}/{record_id}", headers=other_auth_headers).status_code == 404

    assert a_state(client, auth_headers, user_a_records) == before


def test_cannot_create_application_under_another_users_company(client, other_auth_headers, user_a_records):
    response = client.post(
        "/applications",
        json={
            "job_title": "Sneaky",
            "company_id": user_a_records["company"]["id"],
            "job_url": "https://example.com/jobs/sneaky",
        },
        headers=other_auth_headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Company not found"}
    assert client.get("/applications", headers=other_auth_headers).json() == []


def test_cannot_create_interview_under_another_users_application(client, other_auth_headers, user_a_records):
    response = client.post(
        "/interviews",
        json={
            "application_id": user_a_records["application"]["id"],
            "interview_type": "technical",
            "scheduled_at": "2026-11-05T15:00:00",
        },
        headers=other_auth_headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Job application not found"}
    assert client.get("/interviews", headers=other_auth_headers).json() == []


def test_cannot_move_own_application_to_another_users_company(
    client, auth_headers, other_auth_headers, user_a_records, user_b_records
):
    own = user_b_records["application"]
    path = f"/applications/{own['id']}"

    response = client.put(
        path,
        json={"job_title": "Moved", "company_id": user_a_records["company"]["id"], "job_url": own["job_url"]},
        headers=other_auth_headers,
    )

    assert response.status_code == 404
    assert client.get(path, headers=other_auth_headers).json() == own


def test_cannot_move_own_interview_to_another_users_application(
    client, other_auth_headers, user_a_records, user_b_records
):
    own = user_b_records["interview"]
    path = f"/interviews/{own['id']}"

    response = client.put(
        path,
        json={
            "application_id": user_a_records["application"]["id"],
            "interview_type": own["interview_type"],
            "scheduled_at": own["scheduled_at"],
        },
        headers=other_auth_headers,
    )

    assert response.status_code == 404
    assert client.get(path, headers=other_auth_headers).json() == own


@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/applications", {"search": "a-private-note"}),
        ("/applications", {"company": "A Corp"}),
        ("/applications", {"status_filter": "saved"}),
        ("/interviews", {"interview_type": "technical"}),
    ],
)
def test_search_and_filters_never_return_other_users_records(client, other_auth_headers, user_a_records, path, params):
    assert client.get(path, params=params, headers=other_auth_headers).json() == []


def test_filtering_by_another_users_parent_id_returns_nothing(client, other_auth_headers, user_a_records):
    company_id = user_a_records["company"]["id"]
    application_id = user_a_records["application"]["id"]

    assert client.get("/applications", params={"company_id": company_id}, headers=other_auth_headers).json() == []
    assert client.get("/interviews", params={"application_id": application_id}, headers=other_auth_headers).json() == []
