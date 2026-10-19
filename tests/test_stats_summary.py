"""
GET /stats/summary.

WHY:
The summary counts the authenticated user's own applications and interviews.
These tests freeze the clock through the `utc_now` dependency, so every time
boundary is checked relative to one fixed instant regardless of when the suite
runs. Times are placed exactly at, just before, and just after each boundary.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.clock import utc_now
from app.enums import ApplicationStatus, InterviewOutcome
from app.main import app

ALL_STATUSES = [status.value for status in ApplicationStatus]
ALL_OUTCOMES = [outcome.value for outcome in InterviewOutcome]


@pytest.fixture
def frozen_now(client):
    """
    Freeze "now" for the request. It is today's time (to the second), so rows
    whose updated_at comes from MySQL's NOW() are not accidentally stale.
    """
    now = datetime.now(timezone.utc).replace(microsecond=0)
    app.dependency_overrides[utc_now] = lambda: now
    yield now
    app.dependency_overrides.pop(utc_now, None)


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def summary(client, headers):
    response = client.get("/stats/summary", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def create_company(client, headers, name="Acme"):
    return client.post("/companies", json={"name": name}, headers=headers).json()


def create_application(client, headers, company_id, index, status="saved"):
    response = client.post(
        "/applications",
        json={
            "job_title": f"Role {index}",
            "company_id": company_id,
            "job_url": f"https://example.com/jobs/{index}",
            "status": status,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_interview(client, headers, application_id, scheduled_at, **fields):
    response = client.post(
        "/interviews",
        json={"application_id": application_id, "interview_type": "technical", "scheduled_at": scheduled_at, **fields},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def set_updated_at(db_session, application_id, moment):
    db_session.execute(
        text("UPDATE job_applications SET updated_at = :moment WHERE id = :id"),
        {"moment": moment.astimezone(timezone.utc).replace(tzinfo=None), "id": application_id},
    )
    db_session.commit()


def test_summary_requires_a_token(client):
    assert client.get("/stats/summary").status_code == 401


def test_empty_summary_lists_every_status_and_outcome_as_zero(client, auth_headers, frozen_now):
    data = summary(client, auth_headers)

    assert data["applications_by_status"] == dict.fromkeys(ALL_STATUSES, 0)
    assert data["interviews_by_outcome"] == dict.fromkeys(ALL_OUTCOMES, 0)
    assert data["upcoming_interviews"] == {
        "count": 0,
        "window_start": iso(frozen_now),
        "window_end": iso(frozen_now + timedelta(days=7)),
    }
    assert data["stale_applications"] == {
        "count": 0,
        "days": 14,
        "not_updated_since": iso(frozen_now - timedelta(days=14)),
    }
    assert data["generated_at"] == iso(frozen_now)


def test_counts_applications_by_status_and_interviews_by_outcome(client, auth_headers, frozen_now):
    company = create_company(client, auth_headers)
    statuses = ["saved", "applied", "applied", "interviewing", "offer", "rejected", "withdrawn", "applied"]
    applications = [create_application(client, auth_headers, company["id"], i, s) for i, s in enumerate(statuses)]

    past = frozen_now - timedelta(days=3)
    outcomes = ["pending", "advanced", "advanced", "rejected", "offer", "withdrawn"]
    for index, outcome in enumerate(outcomes):
        create_interview(
            client, auth_headers, applications[index]["id"], iso(past + timedelta(hours=index)),
            status="completed", outcome=outcome,
        )

    data = summary(client, auth_headers)

    assert data["applications_by_status"] == {
        "saved": 1, "applied": 3, "interviewing": 1, "offer": 1, "rejected": 1, "withdrawn": 1,
    }
    assert data["interviews_by_outcome"] == {
        "pending": 1, "advanced": 2, "rejected": 1, "offer": 1, "withdrawn": 1,
    }
    assert data["upcoming_interviews"]["count"] == 0


def test_interviews_without_a_decision_count_as_pending(client, auth_headers, frozen_now):
    company = create_company(client, auth_headers)
    application = create_application(client, auth_headers, company["id"], 1)
    create_interview(client, auth_headers, application["id"], iso(frozen_now + timedelta(days=1)))

    assert summary(client, auth_headers)["interviews_by_outcome"]["pending"] == 1


def test_other_users_records_are_never_counted(client, auth_headers, other_auth_headers, frozen_now):
    a_company = create_company(client, auth_headers)
    a_app = create_application(client, auth_headers, a_company["id"], 1, "applied")
    create_interview(client, auth_headers, a_app["id"], iso(frozen_now + timedelta(days=1)), outcome="advanced")

    b_company = create_company(client, other_auth_headers)
    for index, status in enumerate(["applied", "offer", "rejected"], start=10):
        b_app = create_application(client, other_auth_headers, b_company["id"], index, status)
        create_interview(client, other_auth_headers, b_app["id"], iso(frozen_now + timedelta(days=2)), outcome="offer")

    a = summary(client, auth_headers)
    b = summary(client, other_auth_headers)

    assert sum(a["applications_by_status"].values()) == 1
    assert a["applications_by_status"]["applied"] == 1
    assert a["interviews_by_outcome"] == {**dict.fromkeys(ALL_OUTCOMES, 0), "advanced": 1}
    assert a["upcoming_interviews"]["count"] == 1

    assert b["applications_by_status"] == {**dict.fromkeys(ALL_STATUSES, 0), "applied": 1, "offer": 1, "rejected": 1}
    assert b["interviews_by_outcome"] == {**dict.fromkeys(ALL_OUTCOMES, 0), "offer": 3}
    assert b["upcoming_interviews"]["count"] == 3


def test_interviews_are_owned_through_their_application(client, auth_headers, other_auth_headers, db_session, frozen_now):
    """An interview row is counted for whoever owns its application, even if the interview was created by someone else."""
    a_company = create_company(client, auth_headers)
    a_app = create_application(client, auth_headers, a_company["id"], 1)
    b_company = create_company(client, other_auth_headers)
    b_app = create_application(client, other_auth_headers, b_company["id"], 2)
    interview = create_interview(client, other_auth_headers, b_app["id"], iso(frozen_now + timedelta(days=1)))

    # Move B's interview onto A's application directly in the database.
    db_session.execute(
        text("UPDATE interviews SET application_id = :a WHERE id = :id"), {"a": a_app["id"], "id": interview["id"]}
    )
    db_session.commit()

    assert summary(client, auth_headers)["upcoming_interviews"]["count"] == 1
    assert summary(client, other_auth_headers)["upcoming_interviews"]["count"] == 0
    assert sum(summary(client, other_auth_headers)["interviews_by_outcome"].values()) == 0


@pytest.mark.parametrize(
    ("offset", "counted"),
    [
        (timedelta(seconds=-1), False),  # just before now
        (timedelta(0), True),  # exactly now
        (timedelta(days=7, seconds=-1), True),  # last second inside the window
        (timedelta(days=7), False),  # exactly 7 days later: window end is exclusive
        (timedelta(days=7, seconds=1), False),
    ],
    ids=["before-now", "at-now", "last-second", "at-7-days", "after-7-days"],
)
def test_upcoming_interview_window_boundaries(client, auth_headers, frozen_now, offset, counted):
    company = create_company(client, auth_headers)
    application = create_application(client, auth_headers, company["id"], 1)
    create_interview(client, auth_headers, application["id"], iso(frozen_now + offset))

    assert summary(client, auth_headers)["upcoming_interviews"]["count"] == (1 if counted else 0)


def test_cancelled_interviews_are_not_upcoming(client, auth_headers, frozen_now):
    company = create_company(client, auth_headers)
    application = create_application(client, auth_headers, company["id"], 1)
    create_interview(client, auth_headers, application["id"], iso(frozen_now + timedelta(days=1)), status="cancelled")
    create_interview(client, auth_headers, application["id"], iso(frozen_now + timedelta(days=2)), status="rescheduled")

    assert summary(client, auth_headers)["upcoming_interviews"]["count"] == 1


@pytest.mark.parametrize(
    ("age", "stale"),
    [
        (timedelta(days=15), True),
        (timedelta(days=14), True),  # exactly 14 days: counts as stale
        (timedelta(days=14, seconds=-1), False),  # one second short of 14 days
        (timedelta(days=1), False),
    ],
    ids=["15-days", "exactly-14-days", "just-under-14-days", "1-day"],
)
def test_stale_application_boundaries(client, auth_headers, db_session, frozen_now, age, stale):
    company = create_company(client, auth_headers)
    application = create_application(client, auth_headers, company["id"], 1)
    set_updated_at(db_session, application["id"], frozen_now - age)

    assert summary(client, auth_headers)["stale_applications"]["count"] == (1 if stale else 0)


def test_updating_an_application_makes_it_fresh_again(client, auth_headers, db_session, frozen_now):
    company = create_company(client, auth_headers)
    application = create_application(client, auth_headers, company["id"], 1)
    set_updated_at(db_session, application["id"], frozen_now - timedelta(days=30))
    assert summary(client, auth_headers)["stale_applications"]["count"] == 1

    response = client.put(
        f"/applications/{application['id']}",
        json={"job_title": "Role 1", "company_id": company["id"], "job_url": application["job_url"], "status": "applied"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    assert summary(client, auth_headers)["stale_applications"]["count"] == 0


def test_same_instant_in_another_time_zone_gives_the_same_summary(client, auth_headers, db_session):
    utc_instant = datetime.now(timezone.utc).replace(microsecond=0)
    company = create_company(client, auth_headers)
    application = create_application(client, auth_headers, company["id"], 1)
    create_interview(client, auth_headers, application["id"], iso(utc_instant + timedelta(days=7, seconds=-1)))
    set_updated_at(db_session, application["id"], utc_instant - timedelta(days=14))

    results = []
    for zone in (timezone.utc, timezone(timedelta(hours=-5)), timezone(timedelta(hours=9, minutes=30))):
        app.dependency_overrides[utc_now] = lambda zone=zone: utc_instant.astimezone(zone)
        results.append(summary(client, auth_headers))
    app.dependency_overrides.pop(utc_now, None)

    assert results[0] == results[1] == results[2]
    assert results[0]["generated_at"] == iso(utc_instant)
    assert results[0]["upcoming_interviews"]["count"] == 1
    assert results[0]["stale_applications"]["count"] == 1


def test_real_clock_is_utc_to_the_second():
    now = utc_now()

    assert now.tzinfo == timezone.utc
    assert now.microsecond == 0
    assert abs(datetime.now(timezone.utc) - now) < timedelta(seconds=5)
