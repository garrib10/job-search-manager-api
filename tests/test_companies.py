def test_create_company(client):
    response = client.post(
        "/companies",
        json={
            "name": "Travelers",
            "website": "https://travelers.com",
            "industry": "Insurance",
            "location": "Hartford, CT",
            "notes": "Test company",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Travelers"
    assert data["industry"] == "Insurance"
    assert data["location"] == "Hartford, CT"
    assert data["id"] is not None

def test_list_companies(client):
    client.post(
        "/companies",
        json={
            "name": "Travelers",
        },
    )

    client.post(
        "/companies",
        json={
            "name": "Liberty Mutual",
        },
    )

    response = client.get("/companies")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2

    # Companies are returned alphabetically by name.
    assert data[0]["name"] == "Liberty Mutual"
    assert data[1]["name"] == "Travelers"

def test_get_company(client):
    create_response = client.post(
        "/companies",
        json={
            "name": "Travelers",
            "website": "https://travelers.com",
            "industry": "Insurance",
            "location": "Hartford, CT",
        },
    )

    company_id = create_response.json()["id"]

    response = client.get(
        f"/companies/{company_id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == company_id
    assert data["name"] == "Travelers"
    assert data["industry"] == "Insurance"

def test_update_company(client):
    create_response = client.post(
        "/companies",
        json={
            "name": "Travelers",
            "website": "https://travelers.com",
            "industry": "Insurance",
            "location": "Hartford, CT",
            "notes": "Original notes",
        },
    )

    company_id = create_response.json()["id"]

    response = client.put(
        f"/companies/{company_id}",
        json={
            "name": "Travelers Insurance",
            "website": "https://travelers.com",
            "industry": "Insurance",
            "location": "Hartford, CT",
            "notes": "Updated company record",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == company_id
    assert data["name"] == "Travelers Insurance"
    assert data["notes"] == "Updated company record"

def test_delete_company(client):
    create_response = client.post(
        "/companies",
        json={
            "name": "Travelers",
        },
    )

    company_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/companies/{company_id}"
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""

    get_response = client.get(
        f"/companies/{company_id}"
    )

    assert get_response.status_code == 404
    assert get_response.json() == {
        "detail": "Company not found"
    }

def test_company_not_found(client):
    response = client.get("/companies/999999")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Company not found"
    }

def test_update_company_not_found(client):
    response = client.put(
        "/companies/999999",
        json={
            "name": "Missing Company",
            "website": "https://example.com",
            "industry": "Technology",
            "location": "Boston, MA",
            "notes": "This company does not exist.",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Company not found"
    }

def test_delete_company_not_found(client):
    response = client.delete(
        "/companies/999999"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Company not found"
    }

def test_create_company_with_empty_name(client):
    response = client.post(
        "/companies",
        json={
            "name": "",
        },
    )

    assert response.status_code == 422

def test_create_company_with_invalid_website(client):
    response = client.post(
        "/companies",
        json={
            "name": "Travelers",
            "website": "not-a-valid-url",
        },
    )

    assert response.status_code == 422
