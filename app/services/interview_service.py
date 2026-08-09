from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Interview, JobApplication
from app.schemas import InterviewCreate, InterviewUpdate


def get_application_by_id(
    db: Session,
    application_id: int,
) -> JobApplication | None:
    """
    Return a job application by primary key.

    WHY:
    Every interview must reference an existing JobApplication.
    The router can use this lookup before creating or updating
    an interview.
    """
    return db.get(JobApplication, application_id)


def create_interview(
    db: Session,
    interview_data: InterviewCreate,
) -> Interview:
    """
    Create and persist a new interview.

    WHY:
    Database write logic belongs in the service layer so the router
    can remain focused on HTTP requests, responses, and status codes.
    """
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
) -> list[Interview]:
    """
    Return all interviews ordered by scheduled date and time.

    WHY:
    Interview records are naturally time-based, so chronological
    ordering makes the results easier to work with.
    """
    statement = (
        select(Interview)
        .order_by(
            Interview.scheduled_at.asc(),
            Interview.id.asc(),
        )
    )

    return list(db.scalars(statement).all())


def get_interview_by_id(
    db: Session,
    interview_id: int,
) -> Interview | None:
    """Return one interview by primary key."""
    return db.get(Interview, interview_id)


def update_interview(
    db: Session,
    interview: Interview,
    interview_data: InterviewUpdate,
) -> Interview:
    """
    Update an existing interview.

    WHY:
    The project currently uses PUT semantics, so all editable
    interview fields are replaced by the values in the request.
    """
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
