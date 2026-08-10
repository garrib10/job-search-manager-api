def create_test_company(client, name="Travelers"):
    """
    Create and return a company for application tests.

    WHY:
    Every job application must reference a real company.
    This helper keeps repeated setup out of individual tests.
    """
    response = client.post(
        "/companies",
        json={
            "name": name,
            "website": "https://example.com",
            "industry": "Insurance",
            "location": "Hartford, CT",
            "notes": "Application test company.",
        },
    )

    assert response.status_code == 201

    return response.json()

def create_test_application(
    client,
    company_id,
    *,
    job_title="Python Backend Developer",
    job_url="https://example.com/jobs/python-backend",
    status="saved",
    location="Hartford, CT",
    work_arrangement="hybrid",
    date_applied=None,
):
    """
    Create and return a job application for tests.
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
            "notes": "Application test record.",
            "date_applied": date_applied,
        },
    )

    assert response.status_code == 201

    return response.json()

def test_create_application(client):
    company = create_test_company(client)

    response = client.post(
        "/applications",
        json={
            "job_title": "Python Backend Developer",
            "company_id": company["id"],
            "location": "Hartford, CT",
            "work_arrangement": "hybrid",
            "salary_min": 95000,
            "salary_max": 115000,
            "job_url": "https://example.com/jobs/create-application",
            "status": "saved",
            "notes": "Testing application creation.",
            "date_applied": None,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["job_title"] == "Python Backend Developer"
    assert data["company_id"] == company["id"]
    assert data["status"] == "saved"
    assert data["work_arrangement"] == "hybrid"
    assert data["id"] is not None

def test_list_applications(client):
    company = create_test_company(client)

    create_test_application(
        client,
        company["id"],
        job_title="Python Developer",
        job_url="https://example.com/jobs/python-developer",
    )

    create_test_application(
        client,
        company["id"],
        job_title="Java Developer",
        job_url="https://example.com/jobs/java-developer",
    )

    response = client.get("/applications")

    assert response.status_code == 200
    assert len(response.json()) == 2

def test_get_application(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
        job_url="https://example.com/jobs/get-application",
    )

    response = client.get(
        f"/applications/{application['id']}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == application["id"]
    assert data["job_title"] == "Python Backend Developer"

def test_update_application(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
        job_url="https://example.com/jobs/update-application",
    )

    response = client.put(
        f"/applications/{application['id']}",
        json={
            "job_title": "Senior Python Backend Developer",
            "company_id": company["id"],
            "location": "Boston, MA",
            "work_arrangement": "remote",
            "salary_min": 110000,
            "salary_max": 130000,
            "job_url": "https://example.com/jobs/update-application",
            "status": "applied",
            "notes": "Updated application.",
            "date_applied": "2026-08-10",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["job_title"] == "Senior Python Backend Developer"
    assert data["status"] == "applied"
    assert data["location"] == "Boston, MA"
    assert data["work_arrangement"] == "remote"

def test_delete_application(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
        job_url="https://example.com/jobs/delete-application",
    )

    response = client.delete(
        f"/applications/{application['id']}"
    )

    assert response.status_code == 204

    get_response = client.get(
        f"/applications/{application['id']}"
    )

    assert get_response.status_code == 404
    assert get_response.json() == {
        "detail": "Job application not found"
    }

def test_create_application_with_invalid_company(client):
    response = client.post(
        "/applications",
        json={
            "job_title": "Python Developer",
            "company_id": 999999,
            "location": "Boston, MA",
            "work_arrangement": "hybrid",
            "salary_min": 90000,
            "salary_max": 110000,
            "job_url": "https://example.com/jobs/invalid-company",
            "status": "saved",
            "notes": "Invalid company test.",
            "date_applied": None,
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Company not found"
    }

def test_duplicate_job_url(client):
    company = create_test_company(client)

    job_url = "https://example.com/jobs/duplicate-url"

    create_test_application(
        client,
        company["id"],
        job_url=job_url,
    )

    response = client.post(
        "/applications",
        json={
            "job_title": "Duplicate Application",
            "company_id": company["id"],
            "location": "Boston, MA",
            "work_arrangement": "remote",
            "salary_min": 100000,
            "salary_max": 120000,
            "job_url": job_url,
            "status": "saved",
            "notes": "Duplicate URL test.",
            "date_applied": None,
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "An application with this job URL already exists"
    }

def test_application_not_found(client):
    response = client.get("/applications/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Job application not found"
    }

def test_filter_applications_by_status(client):
    company = create_test_company(client)

    create_test_application(
        client,
        company["id"],
        job_title="Saved Application",
        job_url="https://example.com/jobs/saved-filter",
        status="saved",
    )

    create_test_application(
        client,
        company["id"],
        job_title="Applied Application",
        job_url="https://example.com/jobs/applied-filter",
        status="applied",
        date_applied="2026-08-10",
    )

    response = client.get(
        "/applications?status_filter=applied"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["status"] == "applied"

def test_filter_applications_by_company_name(client):
    travelers = create_test_company(
        client,
        name="Travelers",
    )

    liberty = create_test_company(
        client,
        name="Liberty Mutual",
    )

    create_test_application(
        client,
        travelers["id"],
        job_url="https://example.com/jobs/travelers-filter",
    )

    create_test_application(
        client,
        liberty["id"],
        job_title="Java Engineer",
        job_url="https://example.com/jobs/liberty-filter",
    )

    response = client.get(
        "/applications?company=Travelers"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["company_id"] == travelers["id"]

def test_search_applications(client):
    company = create_test_company(client)

    create_test_application(
        client,
        company["id"],
        job_title="Python Backend Developer",
        job_url="https://example.com/jobs/python-search",
    )

    create_test_application(
        client,
        company["id"],
        job_title="Java Software Engineer",
        job_url="https://example.com/jobs/java-search",
    )

    response = client.get(
        "/applications?search=Python"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["job_title"] == "Python Backend Developer"

def test_sort_applications_by_job_title(client):
    company = create_test_company(client)

    create_test_application(
        client,
        company["id"],
        job_title="Python Developer",
        job_url="https://example.com/jobs/python-sort",
    )

    create_test_application(
        client,
        company["id"],
        job_title="Java Developer",
        job_url="https://example.com/jobs/java-sort",
    )

    response = client.get(
        "/applications?sort_by=job_title&sort_order=asc"
    )

    assert response.status_code == 200

    data = response.json()

    assert data[0]["job_title"] == "Java Developer"
    assert data[1]["job_title"] == "Python Developer"

def test_application_pagination(client):
    company = create_test_company(client)

    create_test_application(
        client,
        company["id"],
        job_title="Application One",
        job_url="https://example.com/jobs/pagination-one",
    )

    create_test_application(
        client,
        company["id"],
        job_title="Application Two",
        job_url="https://example.com/jobs/pagination-two",
    )

    response = client.get(
        "/applications?limit=1&offset=0"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1

    second_response = client.get(
        "/applications?limit=1&offset=1"
    )

    assert second_response.status_code == 200
    assert len(second_response.json()) == 1

    assert (
        response.json()[0]["id"]
        != second_response.json()[0]["id"]
    )

def test_invalid_application_date_range(client):
    response = client.get(
        "/applications"
        "?date_applied_from=2026-08-31"
        "&date_applied_to=2026-08-01"
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": (
            "date_applied_from cannot be after "
            "date_applied_to"
        )
    }

def test_create_application_with_invalid_status(client):
    company = create_test_company(client)

    response = client.post(
        "/applications",
        json={
            "job_title": "Invalid Status Test",
            "company_id": company["id"],
            "location": "Boston, MA",
            "work_arrangement": "hybrid",
            "salary_min": 90000,
            "salary_max": 110000,
            "job_url": "https://example.com/jobs/invalid-status",
            "status": "pending",
            "notes": "Should fail Pydantic validation.",
            "date_applied": None,
        },
    )

    assert response.status_code == 422

def test_create_application_with_invalid_salary_range(client):
    company = create_test_company(client)

    response = client.post(
        "/applications",
        json={
            "job_title": "Salary Validation Test",
            "company_id": company["id"],
            "location": "Boston, MA",
            "work_arrangement": "hybrid",
            "salary_min": 120000,
            "salary_max": 100000,
            "job_url": "https://example.com/jobs/invalid-salary-range",
            "status": "saved",
            "notes": "Minimum salary is greater than maximum salary.",
            "date_applied": None,
        },
    )

    assert response.status_code == 422

def test_update_application_with_duplicate_job_url(client):
    company = create_test_company(client)

    first_application = create_test_application(
        client,
        company["id"],
        job_title="Python Developer",
        job_url="https://example.com/jobs/python-original",
    )

    second_application = create_test_application(
        client,
        company["id"],
        job_title="Java Developer",
        job_url="https://example.com/jobs/java-original",
    )

    response = client.put(
        f"/applications/{second_application['id']}",
        json={
            "job_title": "Java Developer",
            "company_id": company["id"],
            "location": "Boston, MA",
            "work_arrangement": "hybrid",
            "salary_min": 95000,
            "salary_max": 115000,
            "job_url": first_application["job_url"],
            "status": "applied",
            "notes": "Should fail because the URL belongs to another application.",
            "date_applied": "2026-08-10",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "An application with this job URL already exists"
    }

def test_update_application_with_invalid_company(client):
    company = create_test_company(client)

    application = create_test_application(
        client,
        company["id"],
        job_url="https://example.com/jobs/update-invalid-company",
    )

    response = client.put(
        f"/applications/{application['id']}",
        json={
            "job_title": "Python Developer",
            "company_id": 999999,
            "location": "Boston, MA",
            "work_arrangement": "remote",
            "salary_min": 95000,
            "salary_max": 115000,
            "job_url": "https://example.com/jobs/update-invalid-company",
            "status": "applied",
            "notes": "Invalid company update test.",
            "date_applied": "2026-08-10",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Company not found"
    }