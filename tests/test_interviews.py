def create_test_company(client, name="Travelers"):
    response = client.post(
        "/companies",
        json={
            "name": name,
            "website": "https://example.com",
            "industry": "Insurance",
            "location": "Hartford, CT",
            "notes": "Interview test company.",
        },
    )

    assert response.status_code == 201

    return response.json()

def create_test_application(
    client,
    company_id,
    *,
    job_title="Python Backend Developer",
    job_url="https://example.com/jobs/interview-test-application",
):
    response = client.post(
        "/applications",
        json={
            "job_title": job_title,
            "company_id": company_id,
            "location": "Hartford, CT",
            "work_arrangement": "hybrid",
            "salary_min": 95000,
            "salary_max": 115000,
            "job_url": job_url,
            "status": "applied",
            "notes": "Interview test application.",
            "date_applied": "2026-08-10",
        },
    )

    assert response.status_code == 201

    return response.json()

def create_test_interview(
    client,
    application_id,
    *,
    interview_type="technical",
    status="scheduled",
    outcome="pending",
    scheduled_at="2026-09-10T10:00:00",
):
    response = client.post(
        "/interviews",
        json={
            "application_id": application_id,
            "interview_type": interview_type,
            "status": status,
            "outcome": outcome,
            "scheduled_at": scheduled_at,
            "interviewer": "Jordan Lee",
            "location": "Zoom",
            "notes": "Interview test record.",
        },
    )

    assert response.status_code == 201

    return response.json()


def test_create_interview(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    response = client.post(
        "/interviews",
        json={
            "application_id": application["id"],
            "interview_type": "technical",
            "status": "scheduled",
            "outcome": "pending",
            "scheduled_at": "2026-09-15T14:00:00",
            "interviewer": "Alex Smith",
            "location": "Zoom",
            "notes": "Technical interview.",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["application_id"] == application["id"]
    assert data["interview_type"] == "technical"
    assert data["status"] == "scheduled"
    assert data["outcome"] == "pending"
    assert data["id"] is not None

def test_list_interviews(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    create_test_interview(
        client,
        application["id"],
        interview_type="technical",
        scheduled_at="2026-09-10T10:00:00",
    )

    create_test_interview(
        client,
        application["id"],
        interview_type="behavioral",
        scheduled_at="2026-09-11T10:00:00",
    )

    response = client.get("/interviews")

    assert response.status_code == 200
    assert len(response.json()) == 2

def test_get_interview(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    interview = create_test_interview(
        client,
        application["id"],
    )

    response = client.get(
        f"/interviews/{interview['id']}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == interview["id"]
    assert data["application_id"] == application["id"]
    assert data["interview_type"] == "technical"

def test_update_interview(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    interview = create_test_interview(
        client,
        application["id"],
        scheduled_at="2026-09-10T10:00:00",
    )

    response = client.put(
        f"/interviews/{interview['id']}",
        json={
            "application_id": application["id"],
            "interview_type": "technical",
            "status": "completed",
            "outcome": "advanced",
            "scheduled_at": "2026-09-10T10:00:00",
            "interviewer": "Jordan Lee",
            "location": "Zoom",
            "notes": "Interview completed successfully.",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "completed"
    assert data["outcome"] == "advanced"
    assert data["notes"] == "Interview completed successfully."

def test_delete_interview(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    interview = create_test_interview(
        client,
        application["id"],
    )

    response = client.delete(
        f"/interviews/{interview['id']}"
    )

    assert response.status_code == 204

    get_response = client.get(
        f"/interviews/{interview['id']}"
    )

    assert get_response.status_code == 404
    assert get_response.json() == {
        "detail": "Interview not found"
    }

def test_create_interview_with_invalid_application(client):
    response = client.post(
        "/interviews",
        json={
            "application_id": 999999,
            "interview_type": "technical",
            "status": "scheduled",
            "outcome": "pending",
            "scheduled_at": "2026-09-12T10:00:00",
            "interviewer": "Jordan Lee",
            "location": "Zoom",
            "notes": "Invalid relationship test.",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Job application not found"
    }

def test_duplicate_interview_schedule(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    scheduled_at = "2026-09-20T09:30:00"

    create_test_interview(
        client,
        application["id"],
        scheduled_at=scheduled_at,
    )

    response = client.post(
        "/interviews",
        json={
            "application_id": application["id"],
            "interview_type": "behavioral",
            "status": "scheduled",
            "outcome": "pending",
            "scheduled_at": scheduled_at,
            "interviewer": "Taylor Jones",
            "location": "Teams",
            "notes": "Duplicate interview test.",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "An interview is already scheduled for this "
            "application at that time"
        )
    }

def test_interview_not_found(client):
    response = client.get("/interviews/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Interview not found"
    }

def test_filter_interviews_by_application(client):
    company = create_test_company(client)

    application_one = create_test_application(
        client,
        company["id"],
        job_title="Python Developer",
        job_url="https://example.com/jobs/interview-app-one",
    )

    application_two = create_test_application(
        client,
        company["id"],
        job_title="Java Developer",
        job_url="https://example.com/jobs/interview-app-two",
    )

    create_test_interview(
        client,
        application_one["id"],
        scheduled_at="2026-09-01T09:00:00",
    )

    create_test_interview(
        client,
        application_two["id"],
        scheduled_at="2026-09-02T09:00:00",
    )

    response = client.get(
        f"/interviews?application_id={application_one['id']}"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["application_id"] == application_one["id"]

def test_filter_interviews_by_status(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    create_test_interview(
        client,
        application["id"],
        status="scheduled",
        scheduled_at="2026-09-03T09:00:00",
    )

    create_test_interview(
        client,
        application["id"],
        status="completed",
        outcome="advanced",
        scheduled_at="2026-09-04T09:00:00",
    )

    response = client.get(
        "/interviews?status_filter=completed"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["status"] == "completed"

def test_filter_interviews_by_type(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    create_test_interview(
        client,
        application["id"],
        interview_type="technical",
        scheduled_at="2026-09-05T09:00:00",
    )

    create_test_interview(
        client,
        application["id"],
        interview_type="behavioral",
        scheduled_at="2026-09-06T09:00:00",
    )

    response = client.get(
        "/interviews?interview_type=behavioral"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["interview_type"] == "behavioral"

def test_filter_interviews_by_outcome(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    create_test_interview(
        client,
        application["id"],
        outcome="pending",
        scheduled_at="2026-09-07T09:00:00",
    )

    create_test_interview(
        client,
        application["id"],
        status="completed",
        outcome="advanced",
        scheduled_at="2026-09-08T09:00:00",
    )

    response = client.get(
        "/interviews?outcome=advanced"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["outcome"] == "advanced"

def test_sort_interviews_descending(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    create_test_interview(
        client,
        application["id"],
        scheduled_at="2026-09-01T09:00:00",
    )

    create_test_interview(
        client,
        application["id"],
        scheduled_at="2026-09-10T09:00:00",
    )

    response = client.get(
        "/interviews?sort_order=desc"
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data[0]["scheduled_at"]
        > data[1]["scheduled_at"]
    )

def test_interview_pagination(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    create_test_interview(
        client,
        application["id"],
        scheduled_at="2026-09-01T09:00:00",
    )

    create_test_interview(
        client,
        application["id"],
        scheduled_at="2026-09-02T09:00:00",
    )

    first_response = client.get(
        "/interviews?limit=1&offset=0"
    )

    second_response = client.get(
        "/interviews?limit=1&offset=1"
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert len(first_response.json()) == 1
    assert len(second_response.json()) == 1

    assert (
        first_response.json()[0]["id"]
        != second_response.json()[0]["id"]
    )

def test_invalid_interview_date_range(client):
    response = client.get(
        "/interviews"
        "?scheduled_from=2026-09-30T23:59:59"
        "&scheduled_to=2026-09-01T00:00:00"
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": (
            "scheduled_from cannot be after "
            "scheduled_to"
        )
    }

def test_create_interview_with_invalid_type(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    response = client.post(
        "/interviews",
        json={
            "application_id": application["id"],
            "interview_type": "coding_round",
            "status": "scheduled",
            "outcome": "pending",
            "scheduled_at": "2026-09-15T10:00:00",
            "interviewer": "Jordan Lee",
            "location": "Zoom",
            "notes": "Should fail validation.",
        },
    )

    assert response.status_code == 422

def test_update_interview_with_duplicate_schedule(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    first_interview = create_test_interview(
        client,
        application["id"],
        scheduled_at="2026-09-20T09:00:00",
    )

    second_interview = create_test_interview(
        client,
        application["id"],
        scheduled_at="2026-09-21T09:00:00",
    )

    response = client.put(
        f"/interviews/{second_interview['id']}",
        json={
            "application_id": application["id"],
            "interview_type": "behavioral",
            "status": "scheduled",
            "outcome": "pending",
            "scheduled_at": first_interview["scheduled_at"],
            "interviewer": "Taylor Jones",
            "location": "Zoom",
            "notes": "Should fail because another interview uses this time.",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "An interview is already scheduled for this "
            "application at that time"
        )
    }

def test_update_interview_with_invalid_application(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    interview = create_test_interview(
        client,
        application["id"],
        scheduled_at="2026-09-25T10:00:00",
    )

    response = client.put(
        f"/interviews/{interview['id']}",
        json={
            "application_id": 999999,
            "interview_type": "technical",
            "status": "scheduled",
            "outcome": "pending",
            "scheduled_at": "2026-09-25T10:00:00",
            "interviewer": "Jordan Lee",
            "location": "Zoom",
            "notes": "Invalid application update test.",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Job application not found"
    }

def test_filter_interviews_by_scheduled_from(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    create_test_interview(
        client,
        application["id"],
        scheduled_at="2026-09-01T09:00:00",
    )

    create_test_interview(
        client,
        application["id"],
        scheduled_at="2026-09-10T09:00:00",
    )

    response = client.get(
        "/interviews?scheduled_from=2026-09-05T00:00:00"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["scheduled_at"].startswith("2026-09-10")

def test_filter_interviews_by_scheduled_to(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
    )

    create_test_interview(
        client,
        application["id"],
        scheduled_at="2026-09-01T09:00:00",
    )

    create_test_interview(
        client,
        application["id"],
        scheduled_at="2026-09-10T09:00:00",
    )

    response = client.get(
        "/interviews?scheduled_to=2026-09-05T23:59:59"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["scheduled_at"].startswith("2026-09-01")