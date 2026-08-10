from datetime import datetime, timedelta, timezone
import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from app.config import get_settings


settings = get_settings()

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Hash a plain-text password before storing it in the database.

    WHY:
    Passwords must never be stored in plain text. The password
    hashing library applies a secure one-way hashing algorithm.
    """
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify that a plain-text password matches a stored password hash.

    WHY:
    Login should compare the submitted password against the stored
    hash without ever recovering or storing the original password.
    """
    return password_hash.verify(
        plain_password,
        hashed_password,
    )


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    WHY:
    The token identifies the authenticated user without requiring
    the client to send their password with every request.
    """
    now = datetime.now(timezone.utc)

    if expires_delta is not None:
        expires_at = now + expires_delta
    else:
        expires_at = now + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(
    token: str,
) -> str | None:
    """
    Decode and validate a JWT access token.

    WHY:
    Protected endpoints need a trusted way to determine which user
    made the request. Invalid or expired tokens are rejected.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        subject = payload.get("sub")

        if not isinstance(subject, str):
            return None

        return subject

    except InvalidTokenError:
        return None
