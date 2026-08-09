from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    JobApplicationCreate,
    JobApplicationResponse,
    JobApplicationUpdate,
)
from app.services import application_service


router = APIRouter(
    prefix="/applications",
    tags=["Applications"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job application",
)
def create_application(
    application_data: JobApplicationCreate,
    db: DatabaseSession,
) -> JobApplicationResponse:
    """
    Create a new job application.
    """

    company = application_service.get_company_by_id(
        db,
        application_data.company_id,
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    existing_application = application_service.get_application_by_job_url(
        db,
        str(application_data.job_url),
    )

    if existing_application is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An application with this job URL already exists",
        )

    return application_service.create_application(
        db,
        application_data,
    )


@router.get(
    "",
    response_model=list[JobApplicationResponse],
    summary="List all job applications",
)
def get_applications(
    db: DatabaseSession,
) -> list[JobApplicationResponse]:
    """
    Return every job application.
    """

    return application_service.get_applications(db)


@router.get(
    "/{application_id}",
    response_model=JobApplicationResponse,
    summary="Get a job application",
)
def get_application(
    application_id: int,
    db: DatabaseSession,
) -> JobApplicationResponse:
    """
    Return one job application by ID.
    """

    application = application_service.get_application_by_id(
        db,
        application_id,
    )

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job application not found",
        )

    return application


@router.put(
    "/{application_id}",
    response_model=JobApplicationResponse,
    summary="Update a job application",
)
def update_application(
    application_id: int,
    application_data: JobApplicationUpdate,
    db: DatabaseSession,
) -> JobApplicationResponse:
    """
    Update an existing job application.
    """

    application = application_service.get_application_by_id(
        db,
        application_id,
    )

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job application not found",
        )

    company = application_service.get_company_by_id(
        db,
        application_data.company_id,
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    existing_application = application_service.get_application_by_job_url(
        db,
        str(application_data.job_url),
    )

    if (
        existing_application is not None
        and existing_application.id != application_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An application with this job URL already exists",
        )

    return application_service.update_application(
        db,
        application,
        application_data,
    )


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a job application",
)
def delete_application(
    application_id: int,
    db: DatabaseSession,
) -> Response:
    """
    Delete an existing job application.
    """

    application = application_service.get_application_by_id(
        db,
        application_id,
    )

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job application not found",
        )

    application_service.delete_application(
        db,
        application,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
