"""
Validation and timezone contract.

WHY:
- Datetimes in requests must carry a UTC offset; they are converted to UTC,
  stored as UTC, and returned in UTC with an explicit "Z".
- Required text is stripped, and blank values are rejected.
- Notes are limited to MySQL TEXT's 65,535-byte capacity measured in UTF-8,
  so multi-byte characters can't overflow the column.
- GET /companies is paginated and ordered by name, then ID.
- Login doesn't validate password length, so a short wrong password is a 401.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.models import Company
from app.schemas.types import MYSQL_TEXT_MAX_BYTES
from tests.conftest import TEST_USER_EMAIL


@pytest.fixture
def application(client, auth_headers):
    company = client.post("/companies", json={"name": "Acme"}, headers=auth_headers).json()
    return client.post(
        "/applications",
        json={"job_title": "Engineer", "company_id": company["id"], "job_url": "https://example.com/jobs/tz"},
        headers=auth_headers,
    ).json()


def schedule(client, headers, application_id, scheduled_at):
    return client.post(
        "/interviews",
        json={"application_id": application_id, "interview_type": "technical", "scheduled_at": scheduled_at},
        headers=headers,
    )


# --- timezones -------------------------------------------------------------


@pytest.mark.parametrize(
    ("sent", "returned"),
    [
        ("2026-11-01T10:00:00-05:00", "2026-11-01T15:00:00Z"),
        ("2026-11-01T17:00:00+02:00", "2026-11-01T15:00:00Z"),
        ("2026-11-01T15:00:00Z", "2026-11-01T15:00:00Z"),
        ("2026-11-01T15:00:00+00:00", "2026-11-01T15:00:00Z"),
    ],
)
def test_offset_aware_datetime_is_stored_and_returned_in_utc(client, auth_headers, application, db_session, sent, returned):
    created = schedule(client, auth_headers, application["id"], sent)

    assert created.status_code == 201
    assert created.json()["scheduled_at"] == returned
    assert client.get(f"/interviews/{created.json()['id']}", headers=auth_headers).json()["scheduled_at"] == returned

    stored = db_session.execute(
        text("SELECT scheduled_at FROM interviews WHERE id = :id"), {"id": created.json()["id"]}
    ).scalar_one()
    assert stored == datetime(2026, 11, 1, 15, 0, 0)


def test_naive_datetime_is_rejected(client, auth_headers, application):
    response = schedule(client, auth_headers, application["id"], "2026-11-01T15:00:00")

    assert response.status_code == 422
    assert "timezone" in response.text.lower()


def test_same_instant_in_different_offsets_is_a_duplicate(client, auth_headers, application):
    assert schedule(client, auth_headers, application["id"], "2026-11-01T10:00:00-05:00").status_code == 201

    duplicate = schedule(client, auth_headers, application["id"], "2026-11-01T15:00:00Z")

    assert duplicate.status_code == 409


def test_timestamps_are_utc_with_explicit_offset(client, auth_headers):
    company = client.post("/companies", json={"name": "Clock Co"}, headers=auth_headers).json()

    for field in ("created_at", "updated_at"):
        assert company[field].endswith("Z")
        created = datetime.fromisoformat(company[field])
        assert abs(datetime.now(timezone.utc) - created) < timedelta(minutes=5)


def test_schedule_filters_accept_offsets_and_reject_naive_values(client, auth_headers, application):
    schedule(client, auth_headers, application["id"], "2026-11-01T15:00:00Z")

    def ids(**params):
        return [item["id"] for item in client.get("/interviews", params=params, headers=auth_headers).json()]

    assert len(ids(scheduled_from="2026-11-01T10:00:00-05:00")) == 1
    assert ids(scheduled_from="2026-11-01T10:00:01-05:00") == []
    assert client.get("/interviews", params={"scheduled_from": "2026-11-01T10:00:00"}, headers=auth_headers).status_code == 422


# --- required text -----------------------------------------------------------


@pytest.mark.parametrize("blank", ["", "   ", "\t\n "])
def test_blank_required_text_is_rejected(client, auth_headers, application, blank):
    company_id = application["company_id"]

    assert client.post("/companies", json={"name": blank}, headers=auth_headers).status_code == 422
    assert client.put(f"/companies/{company_id}", json={"name": blank}, headers=auth_headers).status_code == 422
    assert client.post(
        "/applications",
        json={"job_title": blank, "company_id": company_id, "job_url": "https://example.com/jobs/blank"},
        headers=auth_headers,
    ).status_code == 422


def test_required_text_is_stripped(client, auth_headers):
    company = client.post("/companies", json={"name": "  Acme  "}, headers=auth_headers).json()

    assert company["name"] == "Acme"


def test_records_saved_before_stricter_rules_can_still_be_read(client, auth_headers, db_session):
    user_id = db_session.execute(text("SELECT id FROM users WHERE email = :e"), {"e": TEST_USER_EMAIL}).scalar_one()
    legacy = Company(name="   ", user_id=user_id)
    db_session.add(legacy)
    db_session.commit()

    response = client.get(f"/companies/{legacy.id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["name"] == "   "


# --- notes size --------------------------------------------------------------


@pytest.mark.parametrize(
    ("notes", "accepted"),
    [
        ("a" * MYSQL_TEXT_MAX_BYTES, True),
        ("a" * (MYSQL_TEXT_MAX_BYTES + 1), False),
        ("é" * 32_767 + "a", True),  # 65,535 bytes in 32,768 characters
        ("é" * 32_768, False),  # 65,536 bytes
        ("😀" * 16_383 + "abc", True),  # 65,535 bytes in 16,386 characters
        ("😀" * 16_384, False),  # 65,536 bytes in only 16,384 characters
    ],
    ids=["ascii-at-limit", "ascii-over", "2-byte-at-limit", "2-byte-over", "4-byte-at-limit", "4-byte-over"],
)
def test_notes_are_limited_by_utf8_bytes(client, auth_headers, db_session, notes, accepted):
    response = client.post("/companies", json={"name": "Notes Co", "notes": notes}, headers=auth_headers)

    if accepted:
        assert response.status_code == 201
        stored = db_session.execute(
            text("SELECT notes FROM companies WHERE id = :id"), {"id": response.json()["id"]}
        ).scalar_one()
        assert stored == notes
    else:
        assert response.status_code == 422
        assert "65,535 bytes" in response.text


# --- company pagination ------------------------------------------------------


def test_companies_are_paginated_by_name_then_id(client, auth_headers):
    created = [
        client.post("/companies", json={"name": name}, headers=auth_headers).json()
        for name in ("Beta", "Alpha", "Alpha")
    ]
    beta, alpha_first, alpha_second = created

    def names_and_ids(**params):
        return [(c["name"], c["id"]) for c in client.get("/companies", params=params, headers=auth_headers).json()]

    expected = [("Alpha", alpha_first["id"]), ("Alpha", alpha_second["id"]), ("Beta", beta["id"])]

    assert names_and_ids() == expected
    assert names_and_ids(limit=2) == expected[:2]
    assert names_and_ids(limit=2, offset=2) == expected[2:]
    assert names_and_ids(offset=3) == []


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_company_pagination_bounds(client, auth_headers, params):
    assert client.get("/companies", params=params, headers=auth_headers).status_code == 422


# --- login -------------------------------------------------------------------


def test_short_wrong_password_gets_401_not_422(client):
    client.post("/auth/register", json={"email": "short@example.com", "password": "TestPassword123!"})

    response = client.post("/auth/login", json={"email": "short@example.com", "password": "abc"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


def test_column_type_converts_aware_values_written_outside_the_api(client, auth_headers, application, db_session):
    """The UTCDateTime column itself converts to UTC, for code paths that skip request validation."""
    from app.models import Interview

    eastern = timezone(timedelta(hours=-5))
    interview = Interview(
        application_id=application["id"],
        interview_type="hr",
        scheduled_at=datetime(2026, 11, 1, 10, 0, 0, tzinfo=eastern),
    )
    db_session.add(interview)
    db_session.commit()

    stored = db_session.execute(text("SELECT scheduled_at FROM interviews WHERE id = :id"), {"id": interview.id}).scalar_one()
    assert stored == datetime(2026, 11, 1, 15, 0, 0)

    db_session.expire_all()
    assert db_session.get(Interview, interview.id).scheduled_at == datetime(2026, 11, 1, 15, 0, 0, tzinfo=timezone.utc)
