from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.clock import utc_now
from app.database import get_db
from app.routers.auth import CurrentUser, get_current_user
from app.schemas.stats import StatsSummary
from app.services import stats_service

router = APIRouter(
    prefix="/stats",
    tags=["Stats"],
    # WHY:
    # Every endpoint in this router requires a valid bearer token and only
    # counts the logged-in user's records.
    dependencies=[Depends(get_current_user)],
)

DatabaseSession = Annotated[Session, Depends(get_db)]
Now = Annotated[datetime, Depends(utc_now)]


@router.get(
    "/summary",
    response_model=StatsSummary,
    summary="Summarize your job search",
)
def get_summary(
    db: DatabaseSession,
    current_user: CurrentUser,
    now: Now,
) -> StatsSummary:
    """
    Return counts for the authenticated user's applications and interviews.

    - **applications_by_status**: every status, 0 when none.
    - **interviews_by_outcome**: every outcome, 0 when none. Interviews
      without a decision count as `pending`.
    - **upcoming_interviews**: interviews scheduled from now (inclusive) to
      7 days from now (exclusive), excluding cancelled ones.
    - **stale_applications**: applications whose record hasn't changed for
      14 days or more (updated at or before 14 days ago).

    All counts use one time, `generated_at`, in UTC.
    """
    return stats_service.get_summary(
        db,
        user_id=current_user.id,
        now=now,
    )
