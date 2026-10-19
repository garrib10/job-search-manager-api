"""
Follow-up tracking (/follow-ups).

WHY:
Follow-ups are to-dos on a job application with a due date and a completed
flag. They belong to whoever owns the application. These tests freeze the
clock through the `utc_now` dependency, so "today" (the UTC date) and the
upcoming/overdue boundaries don't depend on when the suite runs.
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.clock import utc_now
from app.main import app

FROZEN = datetime(2026, 11, 10, 15, 30, 0, tzinfo=timezone.utc)
TODAY = FROZEN.date()


@pytest.fixture
def frozen_clock(client):
    app.dependency_overrides[utc_now] = lambda: FROZEN
    yield FROZEN
    app.dependency_overrides.pop(utc_now, None)


def set_clock(moment: datetime) -> None:
    app.dependency_overrides[utc_now] = lambda: moment


def new_application(client, headers, label="a"):
    company = client.post("/companies", json={"name": f"Co {label}"}, headers=headers).json()
    response = client.post(
        "/applications",
        json={"job_title": "Engineer", "company_id": company["id"], "job_url": f"https://example.com/jobs/{label}"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def create(client, headers, application_id, due: date, title="Email the recruiter"):
    response = client.post(
        "/follow-ups",
        json={"application_id": application_id, "title": title, "due_date": due.isoformat()},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def update(client, headers, follow_up, **changes):
    body = {
        "application_id": follow_up["application_id"],
        "title": follow_up["title"],
        "due_date": follow_up["due_date"],
        "completed": follow_up["completed"],
        **changes,
    }
    return client.put(f"/follow-ups/{follow_up['id']}", json=body, headers=headers)


def listed(client, headers, **params):
    response = client.get("/follow-ups", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()]


# --- lifecycle --------------------------------------------------------------


def test_follow_up_lifecycle(client, auth_headers, frozen_clock):
    application = new_application(client, auth_headers)

    created = create(client, auth_headers, application["id"], TODAY + timedelta(days=3))
    assert created["completed"] is False
    assert created["completed_at"] is None
    assert created["due_date"] == (TODAY + timedelta(days=3)).isoformat()

    assert client.get(f"/follow-ups/{created['id']}", headers=auth_headers).json() == created
    assert listed(client, auth_headers) == [created["id"]]

    edited = update(client, auth_headers, created, title="Call the recruiter", due_date=(TODAY + timedelta(days=5)).isoformat())
    assert edited.status_code == 200
    assert edited.json()["title"] == "Call the recruiter"

    completed = update(client, auth_headers, edited.json(), completed=True).json()
    assert completed["completed"] is True
    assert completed["completed_at"] == "2026-11-10T15:30:00Z"

    # Completing again later keeps the original completion time.
    set_clock(FROZEN + timedelta(days=1))
    still = update(client, auth_headers, completed, completed=True).json()
    assert still["completed_at"] == "2026-11-10T15:30:00Z"

    reopened = update(client, auth_headers, still, completed=False).json()
    assert reopened["completed"] is False
    assert reopened["completed_at"] is None

    assert client.delete(f"/follow-ups/{created['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/follow-ups/{created['id']}", headers=auth_headers).status_code == 404
    assert listed(client, auth_headers) == []


def test_title_is_required_and_trimmed(client, auth_headers, frozen_clock):
    application = new_application(client, auth_headers)

    blank = client.post(
        "/follow-ups", json={"application_id": application["id"], "title": "   ", "due_date": TODAY.isoformat()}, headers=auth_headers
    )
    assert blank.status_code == 422

    trimmed = create(client, auth_headers, application["id"], TODAY, title="  Send thank-you note  ")
    assert trimmed["title"] == "Send thank-you note"


def test_update_must_state_completed(client, auth_headers, frozen_clock):
    application = new_application(client, auth_headers)
    follow_up = create(client, auth_headers, application["id"], TODAY)

    response = client.put(
        f"/follow-ups/{follow_up['id']}",
        json={"application_id": application["id"], "title": "Edited", "due_date": TODAY.isoformat()},
        headers=auth_headers,
    )

    assert response.status_code == 422


# --- authentication and ownership --------------------------------------------


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/follow-ups", {"application_id": 1, "title": "x", "due_date": "2026-11-10"}),
        ("GET", "/follow-ups", None),
        ("GET", "/follow-ups/1", None),
        ("PUT", "/follow-ups/1", {"application_id": 1, "title": "x", "due_date": "2026-11-10", "completed": True}),
        ("DELETE", "/follow-ups/1", None),
    ],
)
def test_follow_up_endpoints_require_a_token(client, method, path, body):
    response = client.request(method, path, json=body)

    assert response.status_code == 401


def test_other_users_cannot_read_change_or_delete_follow_ups(client, auth_headers, other_auth_headers, frozen_clock):
    a_app = new_application(client, auth_headers, "a")
    a_follow_up = create(client, auth_headers, a_app["id"], TODAY)
    b_app = new_application(client, other_auth_headers, "b")

    assert client.get(f"/follow-ups/{a_follow_up['id']}", headers=other_auth_headers).status_code == 404
    assert update(client, other_auth_headers, a_follow_up, application_id=b_app["id"], completed=True).status_code == 404
    assert client.delete(f"/follow-ups/{a_follow_up['id']}", headers=other_auth_headers).status_code == 404

    assert listed(client, other_auth_headers) == []
    assert listed(client, other_auth_headers, application_id=a_app["id"]) == []
    assert client.get(f"/follow-ups/{a_follow_up['id']}", headers=auth_headers).json() == a_follow_up


def test_cannot_attach_follow_ups_to_another_users_application(client, auth_headers, other_auth_headers, frozen_clock):
    a_app = new_application(client, auth_headers, "a")
    b_app = new_application(client, other_auth_headers, "b")
    b_follow_up = create(client, other_auth_headers, b_app["id"], TODAY)

    created = client.post(
        "/follow-ups", json={"application_id": a_app["id"], "title": "Sneaky", "due_date": TODAY.isoformat()}, headers=other_auth_headers
    )
    assert created.status_code == 404
    assert created.json() == {"detail": "Job application not found"}

    moved = update(client, other_auth_headers, b_follow_up, application_id=a_app["id"])
    assert moved.status_code == 404
    assert client.get(f"/follow-ups/{b_follow_up['id']}", headers=other_auth_headers).json() == b_follow_up
    assert listed(client, auth_headers) == []


def test_missing_application_and_follow_up_are_404(client, auth_headers, frozen_clock):
    missing_app = client.post(
        "/follow-ups", json={"application_id": 999999, "title": "x", "due_date": TODAY.isoformat()}, headers=auth_headers
    )
    assert missing_app.status_code == 404
    assert missing_app.json() == {"detail": "Job application not found"}

    for method in ("GET", "DELETE"):
        response = client.request(method, "/follow-ups/999999", headers=auth_headers)
        assert response.status_code == 404
        assert response.json() == {"detail": "Follow-up not found"}


# --- filters and boundaries ---------------------------------------------------


@pytest.fixture
def dated(client, auth_headers, frozen_clock):
    """Follow-ups placed around today's boundaries, plus completed ones."""
    application = new_application(client, auth_headers)
    plan = {
        "yesterday": TODAY - timedelta(days=1),
        "today": TODAY,
        "in_6_days": TODAY + timedelta(days=6),
        "in_7_days": TODAY + timedelta(days=7),
        "done_yesterday": TODAY - timedelta(days=1),
        "done_today": TODAY,
    }
    made = {name: create(client, auth_headers, application["id"], due, title=name) for name, due in plan.items()}
    for name in ("done_yesterday", "done_today"):
        made[name] = update(client, auth_headers, made[name], completed=True).json()
    return {name: item["id"] for name, item in made.items()}


@pytest.mark.parametrize(
    ("status_filter", "expected"),
    [
        ("overdue", ["yesterday"]),
        ("upcoming", ["today", "in_6_days"]),
        ("open", ["yesterday", "today", "in_6_days", "in_7_days"]),
        ("completed", ["done_yesterday", "done_today"]),
        (None, ["yesterday", "done_yesterday", "today", "done_today", "in_6_days", "in_7_days"]),
    ],
)
def test_status_filters_and_due_date_boundaries(client, auth_headers, dated, status_filter, expected):
    params = {"status_filter": status_filter} if status_filter else {}

    assert listed(client, auth_headers, **params) == [dated[name] for name in expected]


def test_today_is_the_utc_date(client, auth_headers, dated):
    # 23:30 on Nov 9 in New York is already Nov 10 in UTC.
    set_clock(datetime(2026, 11, 9, 23, 30, tzinfo=timezone(timedelta(hours=-5))))
    assert TODAY == date(2026, 11, 10)

    assert listed(client, auth_headers, status_filter="overdue") == [dated["yesterday"]]


def test_unknown_status_filter_is_rejected(client, auth_headers, frozen_clock):
    assert client.get("/follow-ups", params={"status_filter": "soon"}, headers=auth_headers).status_code == 422


# --- ordering, pagination, application filter -------------------------------


def test_pages_are_ordered_by_due_date_then_id(client, auth_headers, frozen_clock):
    application = new_application(client, auth_headers)
    later = create(client, auth_headers, application["id"], TODAY + timedelta(days=2))
    tie_first = create(client, auth_headers, application["id"], TODAY)
    tie_second = create(client, auth_headers, application["id"], TODAY)
    earliest = create(client, auth_headers, application["id"], TODAY - timedelta(days=1))
    expected = [earliest["id"], tie_first["id"], tie_second["id"], later["id"]]

    assert listed(client, auth_headers) == expected
    assert listed(client, auth_headers, limit=2) + listed(client, auth_headers, limit=2, offset=2) == expected
    assert listed(client, auth_headers, offset=4) == []


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_pagination_bounds(client, auth_headers, frozen_clock, params):
    assert client.get("/follow-ups", params=params, headers=auth_headers).status_code == 422


def test_application_filter(client, auth_headers, frozen_clock):
    first = new_application(client, auth_headers, "first")
    second = new_application(client, auth_headers, "second")
    mine = create(client, auth_headers, first["id"], TODAY)
    create(client, auth_headers, second["id"], TODAY)

    assert listed(client, auth_headers, application_id=first["id"]) == [mine["id"]]


# --- application deletion -----------------------------------------------------


def test_deleting_an_application_deletes_its_follow_ups(client, auth_headers, frozen_clock):
    doomed = new_application(client, auth_headers, "doomed")
    kept_app = new_application(client, auth_headers, "kept")
    gone = create(client, auth_headers, doomed["id"], TODAY)
    kept = create(client, auth_headers, kept_app["id"], TODAY)

    assert client.delete(f"/applications/{doomed['id']}", headers=auth_headers).status_code == 204

    assert client.get(f"/follow-ups/{gone['id']}", headers=auth_headers).status_code == 404
    assert listed(client, auth_headers) == [kept["id"]]


def test_application_with_follow_ups_still_blocks_company_delete(client, auth_headers, frozen_clock):
    application = new_application(client, auth_headers)
    create(client, auth_headers, application["id"], TODAY)

    assert client.delete(f"/companies/{application['company_id']}", headers=auth_headers).status_code == 409
