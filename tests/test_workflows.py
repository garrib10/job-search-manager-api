def create_company(
    client,
    *,
    name="Travelers",
    website="https://example.com",
    location="Hartford, CT",
):
    """
    Create a company for workflow testing.
    """
    response = client.post(
        "/companies",
        json={
            "name": name,
            "website": website,
            "industry": "Technology",
            "location": location,
            "notes": "Workflow test company.",
        },
    )

    assert response.status_code == 201

    return response.json()

def create_application(
    client,
    company_id,
    *,
    job_title="Python Backend Developer",
    job_url="https://example.com/jobs/workflow-python",
    status="saved",
    location="Hartford, CT",
    work_arrangement="hybrid",
    date_applied=None,
):
    """
    Create a job application for workflow testing.
    """
    response = client.post(
        "/applications",
        json={
            "job_title": job_title,
            "company_id": company_id,
            "location": location,
            "work_arrangement": work_arrangement,
            "salary_min": 95000,
            "salary_max": 115000,
            "job_url": job_url,
            "status": status,
            "notes": "Workflow test application.",
            "date_applied": date_applied,
        },
    )

    assert response.status_code == 201

    return response.json()

def create_interview(
    client,
    application_id,
    *,
    interview_type="technical",
    status="scheduled",
    outcome="pending",
    scheduled_at="2026-09-15T10:00:00",
):
    """
    Create an interview for workflow testing.
    """
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
            "notes": "Workflow test interview.",
        },
    )

    assert response.status_code == 201

    return response.json()

def test_complete_job_search_workflow(client):
    """
    Verify a complete Company -> Application -> Interview workflow.
    """
    company = create_company(client)

    application = create_application(
        client,
        company["id"],
        job_url="https://example.com/jobs/complete-workflow",
    )

    interview = create_interview(
        client,
        application["id"],
        scheduled_at="2026-09-20T14:00:00",
    )

    application_update = client.put(
        f"/applications/{application['id']}",
        json={
            "job_title": "Python Backend Developer",
            "company_id": company["id"],
            "location": "Hartford, CT",
            "work_arrangement": "hybrid",
            "salary_min": 95000,
            "salary_max": 115000,
            "job_url": "https://example.com/jobs/complete-workflow",
            "status": "applied",
            "notes": "Application submitted.",
            "date_applied": "2026-08-10",
        },
    )

    assert application_update.status_code == 200
    assert application_update.json()["status"] == "applied"

    interview_update = client.put(
        f"/interviews/{interview['id']}",
        json={
            "application_id": application["id"],
            "interview_type": "technical",
            "status": "completed",
            "outcome": "advanced",
            "scheduled_at": "2026-09-20T14:00:00",
            "interviewer": "Jordan Lee",
            "location": "Zoom",
            "notes": "Technical interview completed.",
        },
    )

    assert interview_update.status_code == 200
    assert interview_update.json()["status"] == "completed"
    assert interview_update.json()["outcome"] == "advanced"

    final_application = client.get(
        f"/applications/{application['id']}"
    )

    final_interview = client.get(
        f"/interviews/{interview['id']}"
    )

    assert final_application.status_code == 200
    assert final_interview.status_code == 200

    assert final_application.json()["company_id"] == company["id"]
    assert final_interview.json()["application_id"] == application["id"]
    assert final_interview.json()["outcome"] == "advanced"

def test_multiple_companies_and_applications_workflow(client):
    """
    Verify applications remain associated with the correct companies.
    """
    travelers = create_company(
        client,
        name="Travelers",
        website="https://travelers.example.com",
    )

    liberty = create_company(
        client,
        name="Liberty Mutual",
        website="https://liberty.example.com",
        location="Boston, MA",
    )

    create_application(
        client,
        travelers["id"],
        job_title="Python Developer",
        job_url="https://example.com/jobs/travelers-python",
    )

    create_application(
        client,
        travelers["id"],
        job_title="Software Engineer",
        job_url="https://example.com/jobs/travelers-software",
    )

    create_application(
        client,
        liberty["id"],
        job_title="Java Developer",
        job_url="https://example.com/jobs/liberty-java",
        location="Boston, MA",
    )

    travelers_response = client.get(
        "/applications?company=Travelers"
    )

    liberty_response = client.get(
        "/applications?company=Liberty"
    )

    assert travelers_response.status_code == 200
    assert liberty_response.status_code == 200

    assert len(travelers_response.json()) == 2
    assert len(liberty_response.json()) == 1

    assert all(
        application["company_id"] == travelers["id"]
        for application in travelers_response.json()
    )

    assert liberty_response.json()[0]["company_id"] == liberty["id"]

def test_interview_progression_workflow(client):
    """
    Verify an interview can progress from scheduled/pending
    to completed/advanced.
    """
    company = create_company(client)

    application = create_application(
        client,
        company["id"],
        job_url="https://example.com/jobs/interview-progression",
        status="applied",
        date_applied="2026-08-10",
    )

    interview = create_interview(
        client,
        application["id"],
        interview_type="behavioral",
        scheduled_at="2026-09-22T11:00:00",
    )

    assert interview["status"] == "scheduled"
    assert interview["outcome"] == "pending"

    response = client.put(
        f"/interviews/{interview['id']}",
        json={
            "application_id": application["id"],
            "interview_type": "behavioral",
            "status": "completed",
            "outcome": "advanced",
            "scheduled_at": "2026-09-22T11:00:00",
            "interviewer": "Taylor Smith",
            "location": "Zoom",
            "notes": "Behavioral interview completed.",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "completed"
    assert data["outcome"] == "advanced"

    get_response = client.get(
        f"/interviews/{interview['id']}"
    )

    assert get_response.status_code == 200
    assert get_response.json()["status"] == "completed"
    assert get_response.json()["outcome"] == "advanced"

def test_application_saved_to_applied_workflow(client):
    """
    Verify a saved job can later be marked as applied.
    """
    company = create_company(client)

    application = create_application(
        client,
        company["id"],
        job_url="https://example.com/jobs/status-progression",
    )

    assert application["status"] == "saved"
    assert application["date_applied"] is None

    response = client.put(
        f"/applications/{application['id']}",
        json={
            "job_title": "Python Backend Developer",
            "company_id": company["id"],
            "location": "Hartford, CT",
            "work_arrangement": "hybrid",
            "salary_min": 95000,
            "salary_max": 115000,
            "job_url": "https://example.com/jobs/status-progression",
            "status": "applied",
            "notes": "Application submitted.",
            "date_applied": "2026-08-10",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "applied"
    assert data["date_applied"] == "2026-08-10"

def test_combined_application_filters_workflow(client):
    """
    Verify multiple application filters can be combined.
    """
    travelers = create_company(
        client,
        name="Travelers",
        website="https://travelers.example.com",
    )

    liberty = create_company(
        client,
        name="Liberty Mutual",
        website="https://liberty.example.com",
        location="Boston, MA",
    )

    create_application(
        client,
        travelers["id"],
        job_title="Python Backend Developer",
        job_url="https://example.com/jobs/filter-target",
        status="applied",
        location="Hartford, CT",
        work_arrangement="hybrid",
        date_applied="2026-08-10",
    )

    create_application(
        client,
        travelers["id"],
        job_title="Java Developer",
        job_url="https://example.com/jobs/filter-java",
        status="saved",
        location="Hartford, CT",
    )

    create_application(
        client,
        liberty["id"],
        job_title="Python Developer",
        job_url="https://example.com/jobs/filter-liberty",
        status="applied",
        location="Boston, MA",
        work_arrangement="remote",
        date_applied="2026-08-10",
    )

    response = client.get(
        "/applications"
        "?company=Travelers"
        "&status_filter=applied"
        "&location=Hartford"
        "&work_arrangement=hybrid"
        "&search=Python"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["job_title"] == "Python Backend Developer"
    assert data[0]["company_id"] == travelers["id"]
    assert data[0]["status"] == "applied"

def test_filtered_pagination_workflow(client):
    """
    Verify pagination works after filtering.
    """
    company = create_company(client)

    for index in range(3):
        create_application(
            client,
            company["id"],
            job_title=f"Applied Engineer {index + 1}",
            job_url=f"https://example.com/jobs/pagination-{index + 1}",
            status="applied",
            date_applied="2026-08-10",
        )

    first_page = client.get(
        "/applications"
        "?status_filter=applied"
        "&sort_by=job_title"
        "&sort_order=asc"
        "&limit=2"
        "&offset=0"
    )

    second_page = client.get(
        "/applications"
        "?status_filter=applied"
        "&sort_by=job_title"
        "&sort_order=asc"
        "&limit=2"
        "&offset=2"
    )

    assert first_page.status_code == 200
    assert second_page.status_code == 200

    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 1

    first_page_ids = {
        application["id"]
        for application in first_page.json()
    }

    second_page_ids = {
        application["id"]
        for application in second_page.json()
    }

    assert first_page_ids.isdisjoint(second_page_ids)

def test_database_relationship_integrity_workflow(client):
    """
    Verify Company -> JobApplication -> Interview relationships
    are preserved throughout the API workflow.
    """
    company = create_company(client)

    application = create_application(
        client,
        company["id"],
        job_url="https://example.com/jobs/integrity-workflow",
    )

    interview = create_interview(
        client,
        application["id"],
        scheduled_at="2026-09-25T13:00:00",
    )

    company_response = client.get(
        f"/companies/{company['id']}"
    )

    application_response = client.get(
        f"/applications/{application['id']}"
    )

    interview_response = client.get(
        f"/interviews/{interview['id']}"
    )

    assert company_response.status_code == 200
    assert application_response.status_code == 200
    assert interview_response.status_code == 200

    assert (
        application_response.json()["company_id"]
        == company_response.json()["id"]
    )

    assert (
        interview_response.json()["application_id"]
        == application_response.json()["id"]
    )

def test_invalid_relationship_workflow(client):
    """
    Verify invalid resource relationships are rejected without
    creating partial records.
    """
    company = create_company(client)

    application = create_application(
        client,
        company["id"],
        job_url="https://example.com/jobs/invalid-workflow",
    )

    invalid_interview_response = client.post(
        "/interviews",
        json={
            "application_id": 999999,
            "interview_type": "technical",
            "status": "scheduled",
            "outcome": "pending",
            "scheduled_at": "2026-09-30T10:00:00",
            "interviewer": "Jordan Lee",
            "location": "Zoom",
            "notes": "Should not be created.",
        },
    )

    assert invalid_interview_response.status_code == 404
    assert invalid_interview_response.json() == {
        "detail": "Job application not found"
    }

    interviews_response = client.get(
        f"/interviews?application_id={application['id']}"
    )

    assert interviews_response.status_code == 200
    assert interviews_response.json() == []

    application_response = client.get(
        f"/applications/{application['id']}"
    )

    assert application_response.status_code == 200
