from sqlalchemy import select
from sqlalchemy.orm import Session
from app.exceptions import ConflictException, NotFoundException
from app.models import User
from app.schemas import Token, UserCreate
from app.security import (
    create_access_token,
    hash_password,
    verify_password,
)

def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    """
    Return a user matching the supplied email address.

    WHY:
    Registration and login both need a consistent way to look up
    users by their unique authentication identifier.
    """
    statement = select(User).where(
        User.email == email
    )

    return db.scalar(statement)

def register_user(
    db: Session,
    user_data: UserCreate,
) -> User:
    """
    Create and persist a new user account.

    WHY:
    Registration business rules belong in the service layer.
    The service prevents duplicate emails and hashes passwords
    before anything is written to the database.
    """
    existing_user = get_user_by_email(
        db,
        str(user_data.email),
    )

    if existing_user is not None:
        raise ConflictException(
            "A user with this email already exists"
        )

    user = User(
        email=str(user_data.email),
        hashed_password=hash_password(
            user_data.password
        ),
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user

def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    """
    Authenticate a user by email and password.

    WHY:
    Authentication should never compare plain-text passwords
    directly against database values. The submitted password is
    verified against the stored hash.
    """
    user = get_user_by_email(
        db,
        email,
    )

    if user is None:
        return None

    if not user.is_active:
        return None

    if not verify_password(
        password,
        user.hashed_password,
    ):
        return None

    return user

def create_token_for_user(
    user: User,
) -> Token:
    """
    Create an access token for an authenticated user.

    WHY:
    JWT creation stays outside the router so authentication logic
    remains reusable and testable.
    """
    access_token = create_access_token(
        subject=user.email
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
    )

def require_user_by_email(
    db: Session,
    email: str,
) -> User:
    """
    Return an active user or raise a not-found exception.

    WHY:
    Protected endpoints need a consistent way to resolve the user
    identified by a decoded JWT.
    """
    user = get_user_by_email(
        db,
        email,
    )

    if user is None or not user.is_active:
        raise NotFoundException(
            "User not found"
        )

    return user