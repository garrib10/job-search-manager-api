def register_test_user(
    client,
    *,
    email="auth@example.com",
    password="TestPassword123!",
):
    """
    Register and return a test user.

    WHY:
    Authentication tests frequently need an existing account.
    This helper keeps that setup consistent and avoids repetition.
    """
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 201

    return response.json()


def login_test_user(
    client,
    *,
    email="auth@example.com",
    password="TestPassword123!",
):
    """
    Log in and return the authentication token response.
    """
    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    return response.json()


def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "auth@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "auth@example.com"
    assert data["is_active"] is True
    assert data["id"] is not None

    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_user(client):
    register_test_user(client)

    response = client.post(
        "/auth/register",
        json={
            "email": "auth@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "A user with this email already exists"
    }


def test_login_user(client):
    register_test_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "auth@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["access_token"]
    assert data["token_type"] == "bearer"


def test_login_with_wrong_password(client):
    register_test_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "auth@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password"
    }


def test_login_with_unknown_email(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "missing@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password"
    }


def test_get_current_user_with_valid_token(client):
    register_test_user(client)

    token_data = login_test_user(client)

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": (
                f"Bearer {token_data['access_token']}"
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == "auth@example.com"
    assert data["is_active"] is True

    assert "password" not in data
    assert "hashed_password" not in data


def test_get_current_user_without_token(client):
    response = client.get("/auth/me")

    assert response.status_code in (401, 403)


def test_get_current_user_with_invalid_token(client):
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer not-a-valid-token"
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or expired authentication token"
    }


def test_register_with_invalid_email(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "not-an-email",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 422


def test_register_with_short_password(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "shortpassword@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422

def test_get_current_user_with_valid_token_for_missing_user(client):
    from app.security import create_access_token

    token = create_access_token(
        "missing-user@example.com"
    )

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid or expired authentication token"
    }

def test_inactive_user_cannot_login(
    client,
    db_session,
):
    from app.models import User
    from app.security import hash_password

    user = User(
        email="inactive@example.com",
        hashed_password=hash_password(
            "TestPassword123!"
        ),
        is_active=False,
    )

    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/auth/login",
        json={
            "email": "inactive@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password"
    }