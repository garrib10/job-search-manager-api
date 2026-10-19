from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.types import RequiredText


class FollowUpCreate(BaseModel):
    """Request body used when creating a follow-up. New follow-ups are open."""

    application_id: int = Field(gt=0)
    title: RequiredText(200) = Field(examples=["Email the recruiter"])
    due_date: date


class FollowUpUpdate(FollowUpCreate):
    """
    Request body used when replacing a follow-up.

    WHY:
    `completed` is required so that a PUT can't reopen a completed follow-up
    by leaving the field out. Set it to true to complete and false to reopen.
    """

    completed: bool


class FollowUpResponse(BaseModel):
    """Public follow-up representation returned by the API."""

    id: int
    application_id: int
    title: str
    due_date: date
    completed: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
