from datetime import date, datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import commit_or_rollback
from app.exceptions import NotFoundException
from app.models import FollowUp, JobApplication
from app.schemas.follow_up import FollowUpCreate, FollowUpUpdate
from app.services.application_service import require_application_by_id

UPCOMING_DAYS = 7

FollowUpStatus = Literal["open", "completed", "upcoming", "overdue"]


def owned_follow_ups(user_id: int):
    """
    Select follow-ups whose job application belongs to the user.

    WHY:
    Follow-ups have no user_id of their own; they belong to whoever owns
    their job application, like interviews.
    """
    return (
        select(FollowUp)
        .join(FollowUp.application)
        .where(JobApplication.user_id == user_id)
    )


def require_follow_up_by_id(
    db: Session,
    follow_up_id: int,
    *,
    user_id: int,
) -> FollowUp:
    """
    Return one of the user's follow-ups or raise a not-found exception.

    WHY:
    Another user's follow-up is reported exactly like a missing one.
    """
    follow_up = db.scalar(
        owned_follow_ups(user_id).where(FollowUp.id == follow_up_id)
    )

    if follow_up is None:
        raise NotFoundException("Follow-up not found")

    return follow_up


def create_follow_up(
    db: Session,
    follow_up_data: FollowUpCreate,
    *,
    user_id: int,
) -> FollowUp:
    """
    Create an open follow-up on one of the user's applications.

    WHY:
    The application must belong to the user; another user's application is
    reported as not found. Ownership comes from the application, never from
    the request.
    """
    require_application_by_id(
        db,
        follow_up_data.application_id,
        user_id=user_id,
    )

    follow_up = FollowUp(
        application_id=follow_up_data.application_id,
        title=follow_up_data.title,
        due_date=follow_up_data.due_date,
    )

    db.add(follow_up)
    commit_or_rollback(db)
    db.refresh(follow_up)

    return follow_up


def get_follow_ups(
    db: Session,
    *,
    user_id: int,
    today: date,
    application_id: int | None = None,
    status_filter: FollowUpStatus | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[FollowUp]:
    """
    Return a page of the user's follow-ups, soonest due first.

    WHY:
    - open: not completed.
    - completed: completed.
    - overdue: not completed and due before today.
    - upcoming: not completed and due today or within the next 6 days
      (7 days including today).
    Completed follow-ups are never overdue or upcoming. Ties on due date are
    broken by ID so pages are stable.
    """
    statement = owned_follow_ups(user_id)

    if application_id is not None:
        statement = statement.where(FollowUp.application_id == application_id)

    if status_filter == "open":
        statement = statement.where(FollowUp.completed.is_(False))
    elif status_filter == "completed":
        statement = statement.where(FollowUp.completed.is_(True))
    elif status_filter == "overdue":
        statement = statement.where(
            FollowUp.completed.is_(False),
            FollowUp.due_date < today,
        )
    elif status_filter == "upcoming":
        statement = statement.where(
            FollowUp.completed.is_(False),
            FollowUp.due_date >= today,
            FollowUp.due_date < today + timedelta(days=UPCOMING_DAYS),
        )

    statement = (
        statement.order_by(FollowUp.due_date.asc(), FollowUp.id.asc())
        .limit(limit)
        .offset(offset)
    )

    return list(db.scalars(statement).all())


def update_follow_up(
    db: Session,
    follow_up: FollowUp,
    follow_up_data: FollowUpUpdate,
    *,
    user_id: int,
    now: datetime,
) -> FollowUp:
    """
    Replace a follow-up's fields, completing or reopening it as requested.

    WHY:
    The (possibly new) application must belong to the user, checked before
    any field changes. completed_at is set when a follow-up becomes completed,
    kept if it was already completed, and cleared when it is reopened.
    """
    require_application_by_id(
        db,
        follow_up_data.application_id,
        user_id=user_id,
    )

    if follow_up_data.completed and not follow_up.completed:
        follow_up.completed_at = now
    elif not follow_up_data.completed:
        follow_up.completed_at = None

    follow_up.application_id = follow_up_data.application_id
    follow_up.title = follow_up_data.title
    follow_up.due_date = follow_up_data.due_date
    follow_up.completed = follow_up_data.completed

    commit_or_rollback(db)
    db.refresh(follow_up)

    return follow_up


def delete_follow_up(
    db: Session,
    follow_up: FollowUp,
) -> None:
    """Delete an existing follow-up."""

    db.delete(follow_up)
    commit_or_rollback(db)
