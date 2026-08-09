from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    InterviewCreate,
    InterviewResponse,
    InterviewUpdate,
)
from app.services import interview_service


router = APIRouter(
    prefix="/interviews",
    tags=["Interviews"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=InterviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an interview",
)
def create_interview(
    interview_data: InterviewCreate,
    db: DatabaseSession,
) -> InterviewResponse:
    """
    Create a new interview.

    WHY:
    Every interview must belong to an existing job application.
    The router validates that relationship before the service writes
    anything to the database.
    """
    application = interview_service.get_application_by_id(
        db,
        interview_data.application_id,
    )

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job application not found",
        )

    return interview_service.create_interview(
        db,
        interview_data,
    )


@router.get(
    "",
    response_model=list[InterviewResponse],
    summary="List all interviews",
)
def get_interviews(
    db: DatabaseSession,
) -> list[InterviewResponse]:
    """Return all interviews."""

    return interview_service.get_interviews(db)


@router.get(
    "/{interview_id}",
    response_model=InterviewResponse,
    summary="Get an interview",
)
def get_interview(
    interview_id: int,
    db: DatabaseSession,
) -> InterviewResponse:
    """Return one interview by ID."""

    interview = interview_service.get_interview_by_id(
        db,
        interview_id,
    )

    if interview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )

    return interview


@router.put(
    "/{interview_id}",
    response_model=InterviewResponse,
    summary="Update an interview",
)
def update_interview(
    interview_id: int,
    interview_data: InterviewUpdate,
    db: DatabaseSession,
) -> InterviewResponse:
    """
    Update an existing interview.

    WHY:
    The interview itself must exist, and if its application_id changes,
    the new job application must also exist.
    """
    interview = interview_service.get_interview_by_id(
        db,
        interview_id,
    )

    if interview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )

    application = interview_service.get_application_by_id(
        db,
        interview_data.application_id,
    )

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job application not found",
        )

    return interview_service.update_interview(
        db,
        interview,
        interview_data,
    )


@router.delete(
    "/{interview_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an interview",
)
def delete_interview(
    interview_id: int,
    db: DatabaseSession,
) -> Response:
    """Delete an existing interview."""

    interview = interview_service.get_interview_by_id(
        db,
        interview_id,
    )

    if interview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )

    interview_service.delete_interview(
        db,
        interview,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )

