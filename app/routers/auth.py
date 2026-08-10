from typing import Annotated
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import (
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.security import decode_access_token
from app.services import auth_service
from app.exceptions import NotFoundException


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(bearer_scheme),
    ],
    db: DatabaseSession,
) -> User:
    """
    Return the currently authenticated user.

    WHY:
    Protected endpoints need a reusable dependency that validates
    the bearer token and resolves the user identified by the JWT.
    """
    email = decode_access_token(
        credentials.credentials
    )

    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    try:
        return auth_service.require_user_by_email(
            db,
            email,
        )
    except NotFoundException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )


CurrentUser = Annotated[
    User,
    Depends(get_current_user),
]


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user",
)
def register_user(
    user_data: UserCreate,
    db: DatabaseSession,
) -> UserResponse:
    """
    Register a new user account.

    WHY:
    The service layer handles duplicate-email protection,
    password hashing, and persistence.
    """
    return auth_service.register_user(
        db,
        user_data,
    )


@router.post(
    "/login",
    response_model=Token,
    summary="Log in",
)
def login(
    user_data: UserLogin,
    db: DatabaseSession,
) -> Token:
    """
    Authenticate a user and return a JWT access token.
    """
    user = auth_service.authenticate_user(
        db,
        str(user_data.email),
        user_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    return auth_service.create_token_for_user(
        user
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
)
def get_me(
    current_user: CurrentUser,
) -> UserResponse:
    """
    Return the currently authenticated user.

    WHY:
    This endpoint verifies that the supplied JWT identifies
    a valid active account.
    """
    return current_user