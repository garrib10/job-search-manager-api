from datetime import datetime
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)

class UserCreate(BaseModel):
    """
    Request body used when registering a new user.

    WHY:
    Registration requires a valid email address and a password.
    Passwords are validated here before they are hashed and stored.
    """

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )


class UserLogin(BaseModel):
    """
    Request body used when authenticating an existing user.

    WHY:
    Login is kept separate from registration so the two operations
    can evolve independently later.
    """

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )


class UserResponse(BaseModel):
    """
    Public user representation returned by the API.

    WHY:
    Sensitive authentication data such as passwords and password
    hashes must never be exposed in API responses.
    """

    id: int
    email: EmailStr
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class Token(BaseModel):
    """
    Authentication token returned after a successful login.
    """

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """
    Data extracted from a decoded JWT.

    WHY:
    Keeping decoded token data in a schema gives the authentication
    layer a predictable structure to validate before trusting it.
    """

    email: EmailStr | None = None