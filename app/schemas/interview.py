from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.enums import (
    InterviewOutcome,
    InterviewStatus,
    InterviewType,
)
from app.schemas.types import NotesText, UtcDatetime


class InterviewBase(BaseModel):
    """
    Shared interview fields used by create, update, and response schemas.
    """

    application_id: int = Field(gt=0)

    interview_type: InterviewType

    status: InterviewStatus = InterviewStatus.SCHEDULED

    outcome: InterviewOutcome = InterviewOutcome.PENDING

    scheduled_at: UtcDatetime

    interviewer: str | None = Field(
        default=None,
        max_length=150,
    )

    location: str | None = Field(
        default=None,
        max_length=150,
    )

    notes: NotesText | None = None


class InterviewCreate(InterviewBase):
    """Request body used when creating an interview."""

    pass


class InterviewUpdate(InterviewBase):
    """Request body used when updating an interview."""

    pass


class InterviewResponse(InterviewBase):
    """Public interview representation returned by the API."""

    # WHY:
    # Responses use plain types so records saved before the stricter input
    # rules can still be read. Stored values come back marked as UTC.
    scheduled_at: datetime
    notes: str | None = None

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)