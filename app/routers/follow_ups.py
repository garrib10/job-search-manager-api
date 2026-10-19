from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.clock import utc_now
from app.database import get_db
from app.routers.auth import CurrentUser, get_current_user
from app.schemas.follow_up import FollowUpCreate, FollowUpResponse, FollowUpUpdate
from app.services import follow_up_service
from app.services.follow_up_service import FollowUpStatus

router = APIRouter(
    prefix="/follow-ups",
    tags=["Follow-ups"],
    # WHY:
    # Every endpoint in this router requires a valid bearer token, and
    # follow-ups are scoped to the logged-in user through their application.
    dependencies=[Depends(get_current_user)],
)

DatabaseSession = Annotated[Session, Depends(get_db)]
Now = Annotated[datetime, Depends(utc_now)]


@router.post(
    "",
    response_model=FollowUpResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a follow-up",
)
def create_follow_up(
    follow_up_data: FollowUpCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> FollowUpResponse:
    """Create an open follow-up on one of your job applications."""
    return follow_up_service.create_follow_up(
        db,
        follow_up_data,
        user_id=current_user.id,
    )


@router.get(
    "",
    response_model=list[FollowUpResponse],
    summary="List follow-ups",
)
def get_follow_ups(
    db: DatabaseSession,
    current_user: CurrentUser,
    now: Now,
    application_id: int | None = None,
    status_filter: FollowUpStatus | None = Query(
        default=None,
        description=(
            "open: not completed. completed: completed. "
            "overdue: not completed and due before today. "
            "upcoming: not completed and due today or within the next 6 days. "
            "Today is the current date in UTC."
        ),
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
) -> list[FollowUpResponse]:
    """Return your follow-ups, soonest due first (then by ID)."""
    return follow_up_service.get_follow_ups(
        db,
        user_id=current_user.id,
        today=now.astimezone(timezone.utc).date(),
        application_id=application_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{follow_up_id}",
    response_model=FollowUpResponse,
    summary="Get a follow-up",
)
def get_follow_up(
    follow_up_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> FollowUpResponse:
    """Return one of your follow-ups."""
    return follow_up_service.require_follow_up_by_id(
        db,
        follow_up_id,
        user_id=current_user.id,
    )


@router.put(
    "/{follow_up_id}",
    response_model=FollowUpResponse,
    summary="Update, complete, or reopen a follow-up",
)
def update_follow_up(
    follow_up_id: int,
    follow_up_data: FollowUpUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
    now: Now,
) -> FollowUpResponse:
    """
    Replace a follow-up. Send `"completed": true` to complete it (the server
    records `completed_at`) or `"completed": false` to reopen it.
    """
    follow_up = follow_up_service.require_follow_up_by_id(
        db,
        follow_up_id,
        user_id=current_user.id,
    )

    return follow_up_service.update_follow_up(
        db,
        follow_up,
        follow_up_data,
        user_id=current_user.id,
        now=now,
    )


@router.delete(
    "/{follow_up_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a follow-up",
)
def delete_follow_up(
    follow_up_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Response:
    """Delete one of your follow-ups."""
    follow_up = follow_up_service.require_follow_up_by_id(
        db,
        follow_up_id,
        user_id=current_user.id,
    )

    follow_up_service.delete_follow_up(
        db,
        follow_up,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
