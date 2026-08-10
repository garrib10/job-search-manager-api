from datetime import timedelta
import jwt
from app.config import get_settings
from app.security import (
    create_access_token,
    decode_access_token,
)

def test_create_access_token_with_custom_expiration():
    token = create_access_token(
        "custom@example.com",
        expires_delta=timedelta(minutes=5),
    )

    assert token
    assert (
        decode_access_token(token)
        == "custom@example.com"
    )

def test_decode_access_token_with_invalid_subject():
    settings = get_settings()

    token = jwt.encode(
        {
            "sub": 12345,
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    assert decode_access_token(token) is None

def test_decode_expired_access_token():
    token = create_access_token(
        "expired@example.com",
        expires_delta=timedelta(seconds=-1),
    )

    assert decode_access_token(token) is None