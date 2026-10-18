"""
Search, filtering, sorting, and pagination under owner scoping.

WHY:
The isolation tests prove another user's records never appear, but in those
tests the other user has no matching records of their own. These tests give
two users interleaved, overlapping data (same company names, job titles,
locations, statuses, interview types, and times), so a query that sorted or
paginated before scoping, or filtered without the owner, would mix their
records. Every expected result is computed from the current user's own
records only.

The list endpoints return plain arrays; there is no total-count metadata to
check.
"""

from datetime import date

import pytest

from tests.conftest import create_user_headers


@pytest.fixture
def third_user_headers(db_session):
    """A user with no records at all."""
    return create_user_headers(db_session, "empty-user@example.com")


APPLICATION_ROWS = [
    # (owner, title, location, status, work_arrangement, salary_min, date_applied)
    ("a", "Backend Engineer", "Boston", "applied", "remote", 90000, "2026-09-01"),
    ("b", "Backend Engineer", "Boston", "applied", "remote", 95000, "2026-09-01"),
    ("a", "Data Engineer", "Denver", "saved", "hybrid", 80000, None),
    ("b", "Data Engineer", "Boston", "saved", "hybrid", 70000, None),
    ("a", "Platform Engineer", "Boston", "interviewing", "onsite", 120000, "2026-09-15"),
    ("b", "Platform Engineer", "Denver", "interviewing", "onsite", 125000, "2026-09-15"),
    ("a", "Analyst", "Boston", "applied", "remote", 60000, "2026-09-20"),
    ("b", "Analyst", "Boston", "rejected", "remote", 65000, "2026-09-20"),
    ("a", "Engineering Manager", "Remote", "offer", "remote", 150000, "2026-09-25"),
]


@pytest.fixture
def interleaved(client, auth_headers, other_auth_headers):
    """
    Users A and B with overlapping data, created alternately so their rows
    interleave by ID.
    """
    headers = {"a": auth_headers, "b": other_auth_headers}
    data = {"a": {"companies": [], "applications": [], "interviews": []}, "b": {"companies": [], "applications": [], "interviews": []}}

    for name in ("Acme", "Globex", "Acme"):
        for owner in ("a", "b"):
            data[owner]["companies"].append(client.post("/companies", json={"name": name}, headers=headers[owner]).json())

    for index, (owner, title, location, status, arrangement, salary, applied) in enumerate(APPLICATION_ROWS):
        company = data[owner]["companies"][index % 2]
        body = {
            "job_title": title,
            "company_id": company["id"],
            "job_url": f"https://example.com/jobs/{owner}-{index}",
            "location": location,
            "status": status,
            "work_arrangement": arrangement,
            "salary_min": salary,
            "date_applied": applied,
            "notes": f"shared keyword {title}",
        }
        response = client.post("/applications", json=body, headers=headers[owner])
        assert response.status_code == 201, response.text
        data[owner]["applications"].append(response.json())

    times = ["2026-11-01T15:00:00Z", "2026-11-02T15:00:00Z", "2026-11-02T15:00:00Z"]
    for when, interview_type in zip(times, ("technical", "hr", "technical")):
        for owner in ("a", "b"):
            # Each interview goes on a different application, so equal times are allowed.
            application = data[owner]["applications"][len(data[owner]["interviews"])]
            response = client.post(
                "/interviews",
                json={"application_id": application["id"], "interview_type": interview_type, "scheduled_at": when},
                headers=headers[owner],
            )
            assert response.status_code == 201, response.text
            data[owner]["interviews"].append(response.json())

    return {"headers": headers, "data": data}


def ids(client, path, headers, **params):
    response = client.get(path, params=params, headers=headers)
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()]


# --- applications -----------------------------------------------------------


@pytest.mark.parametrize("owner", ["a", "b"])
def test_search_returns_only_the_users_matching_applications(client, interleaved, owner):
    mine = interleaved["data"][owner]["applications"]
    expected = sorted((a["id"] for a in mine if "Engineer" in a["job_title"]), reverse=True)

    assert ids(client, "/applications", interleaved["headers"][owner], search="Engineer") == expected


@pytest.mark.parametrize(
    ("params", "matches"),
    [
        ({"status_filter": "applied"}, lambda a: a["status"] == "applied"),
        ({"location": "Boston"}, lambda a: a["location"] == "Boston"),
        ({"work_arrangement": "remote"}, lambda a: a["work_arrangement"] == "remote"),
        ({"date_applied_from": "2026-09-10", "date_applied_to": "2026-09-22"},
         lambda a: a["date_applied"] is not None and "2026-09-10" <= a["date_applied"] <= "2026-09-22"),
        ({"search": "shared keyword"}, lambda a: True),
    ],
    ids=["status", "location", "work_arrangement", "date_range", "notes_search"],
)
@pytest.mark.parametrize("owner", ["a", "b"])
def test_application_filters_only_match_the_users_records(client, interleaved, owner, params, matches):
    mine = interleaved["data"][owner]["applications"]
    expected = sorted((a["id"] for a in mine if matches(a)), reverse=True)

    assert ids(client, "/applications", interleaved["headers"][owner], **params) == expected


def test_company_name_filter_does_not_cross_users_with_the_same_company_name(client, interleaved):
    a = interleaved["data"]["a"]
    acme_ids = {c["id"] for c in a["companies"] if c["name"] == "Acme"}
    expected = sorted((x["id"] for x in a["applications"] if x["company_id"] in acme_ids), reverse=True)

    assert expected  # both users have an "Acme"; only A's applications may match
    assert ids(client, "/applications", interleaved["headers"]["a"], company="Acme") == expected


@pytest.mark.parametrize(
    ("sort_by", "sort_order", "key"),
    [
        ("job_title", "asc", lambda a: (a["job_title"], a["id"])),
        ("salary_min", "desc", lambda a: (-float(a["salary_min"]), -a["id"])),
        ("date_applied", "asc", lambda a: (a["date_applied"] or "", a["id"])),
    ],
)
def test_sorting_orders_only_the_users_dataset(client, interleaved, sort_by, sort_order, key):
    mine = interleaved["data"]["a"]["applications"]
    expected = [a["id"] for a in sorted(mine, key=key)]

    assert ids(client, "/applications", interleaved["headers"]["a"], sort_by=sort_by, sort_order=sort_order) == expected


def test_application_pages_are_cut_from_the_users_records_only(client, interleaved):
    headers = interleaved["headers"]["a"]
    full = ids(client, "/applications", headers)
    assert full == sorted((a["id"] for a in interleaved["data"]["a"]["applications"]), reverse=True)

    pages = [ids(client, "/applications", headers, limit=2, offset=offset) for offset in range(0, len(full) + 2, 2)]

    assert [len(page) for page in pages] == [2, 2, 1, 0]
    assert [item for page in pages for item in page] == full


def test_equal_sort_values_keep_a_stable_page_order(client, interleaved):
    """Every application has today's date_saved, so ID breaks every tie."""
    headers = interleaved["headers"]["b"]
    mine = sorted((a["id"] for a in interleaved["data"]["b"]["applications"]), reverse=True)

    for _ in range(3):
        first = ids(client, "/applications", headers, sort_by="date_saved", limit=2)
        second = ids(client, "/applications", headers, sort_by="date_saved", limit=2, offset=2)
        assert first + second == mine[:4]
        assert not set(first) & set(second)

    ascending = ids(client, "/applications", headers, sort_by="date_saved", sort_order="asc", limit=2) + ids(
        client, "/applications", headers, sort_by="date_saved", sort_order="asc", limit=2, offset=2
    )
    assert ascending == sorted(mine)[:4]

    assert {a["date_saved"] for a in interleaved["data"]["b"]["applications"]} == {date.today().isoformat()}


# --- interviews -------------------------------------------------------------


@pytest.mark.parametrize(
    ("params", "matches"),
    [
        ({"interview_type": "technical"}, lambda i: i["interview_type"] == "technical"),
        ({"status_filter": "scheduled"}, lambda i: i["status"] == "scheduled"),
        ({"outcome": "pending"}, lambda i: i["outcome"] == "pending"),
        ({"scheduled_from": "2026-11-02T00:00:00Z"}, lambda i: i["scheduled_at"] >= "2026-11-02"),
    ],
    ids=["type", "status", "outcome", "scheduled_from"],
)
@pytest.mark.parametrize("owner", ["a", "b"])
def test_interview_filters_only_match_the_users_records(client, interleaved, owner, params, matches):
    mine = interleaved["data"][owner]["interviews"]
    expected = [i["id"] for i in sorted(mine, key=lambda i: (i["scheduled_at"], i["id"])) if matches(i)]

    assert ids(client, "/interviews", interleaved["headers"][owner], **params) == expected


def test_interview_application_filter_uses_only_the_users_application(client, interleaved):
    a = interleaved["data"]["a"]
    application_id = a["interviews"][0]["application_id"]

    assert ids(client, "/interviews", interleaved["headers"]["a"], application_id=application_id) == [a["interviews"][0]["id"]]


def test_interview_sorting_and_pages_use_only_the_users_records(client, interleaved):
    headers = interleaved["headers"]["a"]
    mine = interleaved["data"]["a"]["interviews"]
    descending = [i["id"] for i in sorted(mine, key=lambda i: (i["scheduled_at"], i["id"]), reverse=True)]

    assert ids(client, "/interviews", headers, sort_order="desc") == descending
    # Two of A's interviews share a time; the ID tie-breaker keeps pages stable.
    assert ids(client, "/interviews", headers, sort_order="desc", limit=1) + ids(
        client, "/interviews", headers, sort_order="desc", limit=2, offset=1
    ) == descending


# --- companies --------------------------------------------------------------


def test_company_pages_use_only_the_users_companies(client, interleaved):
    headers = interleaved["headers"]["b"]
    mine = interleaved["data"]["b"]["companies"]
    expected = [c["id"] for c in sorted(mine, key=lambda c: (c["name"], c["id"]))]

    assert ids(client, "/companies", headers) == expected
    assert ids(client, "/companies", headers, limit=2) + ids(client, "/companies", headers, limit=2, offset=2) == expected


# --- empty results ----------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/companies", {}),
        ("/applications", {}),
        ("/applications", {"search": "Engineer"}),
        ("/applications", {"company": "Acme"}),
        ("/interviews", {"interview_type": "technical"}),
    ],
)
def test_user_without_records_gets_empty_lists(client, interleaved, third_user_headers, path, params):
    assert ids(client, path, third_user_headers, **params) == []


def test_offset_past_the_users_last_record_is_empty(client, interleaved):
    headers = interleaved["headers"]["a"]
    count = len(interleaved["data"]["a"]["applications"])

    # B has applications beyond A's count; they must not fill A's later pages.
    assert ids(client, "/applications", headers, offset=count) == []
    assert ids(client, "/interviews", headers, offset=len(interleaved["data"]["a"]["interviews"])) == []
