from datetime import datetime

from pydantic import BaseModel, Field

from app.enums import ApplicationStatus, InterviewOutcome


class UpcomingInterviews(BaseModel):
    """Interviews scheduled from `window_start` (inclusive) to `window_end` (exclusive)."""

    count: int
    window_start: datetime
    window_end: datetime


class StaleApplications(BaseModel):
    """Applications whose record hasn't changed since `not_updated_since` (inclusive)."""

    count: int
    days: int
    not_updated_since: datetime


class StatsSummary(BaseModel):
    """
    Counts for the authenticated user's own job search.

    WHY:
    Every status and outcome is always present (0 when there are none), so
    clients don't have to handle missing keys. The time windows are returned
    with their exact boundaries so the counts can be checked.
    """

    generated_at: datetime = Field(description="The single point in time all counts were evaluated at (UTC).")
    applications_by_status: dict[ApplicationStatus, int]
    interviews_by_outcome: dict[InterviewOutcome, int]
    upcoming_interviews: UpcomingInterviews
    stale_applications: StaleApplications
