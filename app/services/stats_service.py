from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.enums import ApplicationStatus, InterviewOutcome, InterviewStatus
from app.models import Interview, JobApplication
from app.schemas.stats import StaleApplications, StatsSummary, UpcomingInterviews

UPCOMING_WINDOW = timedelta(days=7)
STALE_AFTER_DAYS = 14


def owned_interviews_count():
    """COUNT(*) over interviews whose job application belongs to the user."""
    return select(func.count()).select_from(Interview).join(Interview.application)


def get_summary(
    db: Session,
    *,
    user_id: int,
    now: datetime,
) -> StatsSummary:
    """
    Count the user's applications and interviews with database aggregation.

    WHY:
    Each figure is one GROUP BY or COUNT query filtered by owner, so the work
    stays in MySQL and no records are loaded into Python. Interviews have no
    owner column; they are scoped through their job application. Every count
    uses the same `now`.
    """
    now = now.astimezone(timezone.utc)

    status_rows = db.execute(
        select(JobApplication.status, func.count())
        .where(JobApplication.user_id == user_id)
        .group_by(JobApplication.status)
    ).all()
    status_counts = dict(status_rows)

    outcome_rows = db.execute(
        select(Interview.outcome, func.count())
        .join(Interview.application)
        .where(JobApplication.user_id == user_id)
        .group_by(Interview.outcome)
    ).all()
    outcome_counts = dict(outcome_rows)

    window_end = now + UPCOMING_WINDOW
    upcoming = db.scalar(
        owned_interviews_count().where(
            JobApplication.user_id == user_id,
            Interview.scheduled_at >= now,
            Interview.scheduled_at < window_end,
            Interview.status != InterviewStatus.CANCELLED,
        )
    )

    stale_cutoff = now - timedelta(days=STALE_AFTER_DAYS)
    stale = db.scalar(
        select(func.count())
        .select_from(JobApplication)
        .where(
            JobApplication.user_id == user_id,
            JobApplication.updated_at <= stale_cutoff,
        )
    )

    return StatsSummary(
        generated_at=now,
        applications_by_status={status: status_counts.get(status, 0) for status in ApplicationStatus},
        interviews_by_outcome={outcome: outcome_counts.get(outcome, 0) for outcome in InterviewOutcome},
        upcoming_interviews=UpcomingInterviews(count=upcoming, window_start=now, window_end=window_end),
        stale_applications=StaleApplications(count=stale, days=STALE_AFTER_DAYS, not_updated_since=stale_cutoff),
    )
