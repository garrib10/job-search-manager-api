from datetime import datetime
from typing import Literal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.enums import (
    InterviewOutcome,
    InterviewStatus,
    InterviewType,
)
from app.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.models import Interview, JobApplication
from app.schemas import InterviewCreate, InterviewUpdate
from app.services.application_service import require_application_by_id

def owned_interviews(user_id: int):
    """
    Select interviews whose job application belongs to the user.

    WHY:
    Interviews have no user_id of their own; they belong to whoever owns
    their job application.
    """
    return (
        select(Interview)
        .join(Interview.application)
        .where(JobApplication.user_id == user_id)
    )


def require_interview_by_id(
    db: Session,
    interview_id: int,
    *,
    user_id: int,
) -> Interview:
    """
    Return one of the user's interviews or raise a not-found exception.

    WHY:
    Resource existence checks belong in the service layer. Another
    user's interview is reported exactly like a missing one. The global
    exception handler converts this exception into a consistent 404
    HTTP response.
    """
    interview = db.scalar(
        owned_interviews(user_id).where(Interview.id == interview_id)
    )

    if interview is None:
        raise NotFoundException("Interview not found")

    return interview

def get_interview_by_application_and_time(
    db: Session,
    application_id: int,
    scheduled_at: datetime,
) -> Interview | None:
    """
    Return an interview scheduled for the same application
    at the exact same date and time.

    WHY:
    This lookup supports duplicate scheduling protection while still
    allowing different applications to have interviews at the same time.
    """
    statement = select(Interview).where(
        Interview.application_id == application_id,
        Interview.scheduled_at == scheduled_at,
    )

    return db.scalar(statement)

def create_interview(
    db: Session,
    interview_data: InterviewCreate,
    *,
    user_id: int,
) -> Interview:
    """
    Create and persist a new interview.

    WHY:
    The service layer owns database-dependent business rules,
    including validating the JobApplication relationship and
    preventing duplicate interview scheduling. The application must
    belong to the same user; another user's application is reported as
    not found.
    """
    require_application_by_id(
        db,
        interview_data.application_id,
        user_id=user_id,
    )

    existing_interview = get_interview_by_application_and_time(
        db,
        interview_data.application_id,
        interview_data.scheduled_at,
    )

    if existing_interview is not None:
        raise ConflictException(
            "An interview is already scheduled for this application at that time"
        )

    interview = Interview(
        application_id=interview_data.application_id,
        interview_type=interview_data.interview_type,
        status=interview_data.status,
        outcome=interview_data.outcome,
        scheduled_at=interview_data.scheduled_at,
        interviewer=interview_data.interviewer,
        location=interview_data.location,
        notes=interview_data.notes,
    )

    db.add(interview)
    db.commit()
    db.refresh(interview)

    return interview

def get_interviews(
    db: Session,
    *,
    user_id: int,
    application_id: int | None = None,
    interview_type: InterviewType | None = None,
    status_filter: InterviewStatus | None = None,
    outcome: InterviewOutcome | None = None,
    scheduled_from: datetime | None = None,
    scheduled_to: datetime | None = None,
    sort_order: Literal["asc", "desc"] = "asc",
    limit: int = 20,
    offset: int = 0,
) -> list[Interview]:
    """
    Return interviews using optional filtering, sorting, and pagination.

    WHY:
    Building the SQLAlchemy query conditionally allows the API to
    combine several optional filters without creating separate
    endpoints for each possible query.
    """
    if (
        scheduled_from is not None
        and scheduled_to is not None
        and scheduled_from > scheduled_to
    ):
        raise ValidationException(
            "scheduled_from cannot be after scheduled_to"
        )

    statement = owned_interviews(user_id)

    if application_id is not None:
        statement = statement.where(
            Interview.application_id == application_id
        )

    if interview_type is not None:
        statement = statement.where(
            Interview.interview_type == interview_type
        )

    if status_filter is not None:
        statement = statement.where(
            Interview.status == status_filter
        )

    if outcome is not None:
        statement = statement.where(
            Interview.outcome == outcome
        )

    if scheduled_from is not None:
        statement = statement.where(
            Interview.scheduled_at >= scheduled_from
        )

    if scheduled_to is not None:
        statement = statement.where(
            Interview.scheduled_at <= scheduled_to
        )

    if sort_order == "asc":
        statement = statement.order_by(
            Interview.scheduled_at.asc(),
            Interview.id.asc(),
        )
    else:
        statement = statement.order_by(
            Interview.scheduled_at.desc(),
            Interview.id.desc(),
        )

    statement = statement.limit(limit).offset(offset)

    return list(db.scalars(statement).all())

def update_interview(
    db: Session,
    interview: Interview,
    interview_data: InterviewUpdate,
    *,
    user_id: int,
) -> Interview:
    """
    Update an existing interview.

    WHY:
    The service validates database-dependent business rules, including
    that the new application belongs to the same user, before changing
    any field, so a rejected update leaves the interview untouched.
    """
    require_application_by_id(
        db,
        interview_data.application_id,
        user_id=user_id,
    )

    existing_interview = get_interview_by_application_and_time(
        db,
        interview_data.application_id,
        interview_data.scheduled_at,
    )

    if (
        existing_interview is not None
        and existing_interview.id != interview.id
    ):
        raise ConflictException(
            "An interview is already scheduled for this application at that time"
        )

    interview.application_id = interview_data.application_id
    interview.interview_type = interview_data.interview_type
    interview.status = interview_data.status
    interview.outcome = interview_data.outcome
    interview.scheduled_at = interview_data.scheduled_at
    interview.interviewer = interview_data.interviewer
    interview.location = interview_data.location
    interview.notes = interview_data.notes

    db.commit()
    db.refresh(interview)

    return interview

def delete_interview(
    db: Session,
    interview: Interview,
) -> None:
    """Delete an existing interview."""

    db.delete(interview)
    db.commit()