from datetime import date, datetime
from decimal import Decimal
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    model_validator,
)

from app.enums import ApplicationStatus, WorkArrangement
from app.schemas.types import NotesText, RequiredText


class JobApplicationBase(BaseModel):
    """
    Shared fields for job application request and response schemas.

    WHY:
    Common validation belongs in one place so create and response
    schemas remain consistent.
    """

    job_title: RequiredText(200) = Field(
        examples=["Associate Software Engineer"],
    )

    company_id: int = Field(gt=0)

    location: str | None = Field(
        default=None,
        max_length=150,
    )

    work_arrangement: WorkArrangement | None = None

    salary_min: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )

    salary_max: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )

    job_url: HttpUrl

    status: ApplicationStatus = ApplicationStatus.SAVED

    notes: NotesText | None = None

    date_applied: date | None = None

    @model_validator(mode="after")
    def validate_salary_range(self):
        """
        Ensure the minimum salary does not exceed the maximum salary.
        """
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError(
                "salary_min cannot be greater than salary_max"
            )

        return self


class JobApplicationCreate(JobApplicationBase):
    """Request body used when creating a job application."""

    pass


class JobApplicationUpdate(JobApplicationBase):
    """Request body used when updating a job application."""

    pass


class JobApplicationResponse(JobApplicationBase):
    """Public job application representation returned by the API."""

    # WHY:
    # Responses use plain types so records saved before the stricter input
    # rules can still be read.
    job_title: str
    notes: str | None = None

    id: int
    date_saved: date
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)