from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CompanyBase(BaseModel):
    """
    Shared company fields used by request and response schemas.

    WHY:
    Keeping common fields in one base schema prevents duplicated
    validation rules across create and response models.
    """

    name: str = Field(
        min_length=1,
        max_length=150,
        examples=["Travelers"],
    )

    website: HttpUrl | None = None

    industry: str | None = Field(
        default=None,
        max_length=100,
    )

    location: str | None = Field(
        default=None,
        max_length=150,
    )

    notes: str | None = None


class CompanyCreate(CompanyBase):
    """Request body used when creating a company."""

    pass


class CompanyUpdate(BaseModel):
    """
    Request body used when updating a company.

    WHY:
    The client may change editable company information, but database-owned
    fields such as id and timestamps are never accepted from the client.
    """

    name: str = Field(
        min_length=1,
        max_length=150,
    )

    website: HttpUrl | None = None

    industry: str | None = Field(
        default=None,
        max_length=100,
    )

    location: str | None = Field(
        default=None,
        max_length=150,
    )

    notes: str | None = None


class CompanyResponse(CompanyBase):
    """
    Public Company representation returned by API endpoints.

    WHY:
    Response schemas expose generated database fields while keeping the
    persistence model separate from the public API contract.
    """

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)