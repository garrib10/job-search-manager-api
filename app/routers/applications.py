from datetime import date
from typing import Annotated, Literal
from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
    status,
)
from sqlalchemy.orm import Session
from app.database import get_db
from app.enums import ApplicationStatus, WorkArrangement
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

    WHY:
    Database-dependent business rules, such as company existence
    and duplicate job URL checks, are handled by the service layer.
    """
    return application_service.create_application(
        db,
        application_data,
    )


@router.get(
    "",
    response_model=list[JobApplicationResponse],
    summary="List job applications",
)
def get_applications(
    db: DatabaseSession,
    status_filter: ApplicationStatus | None = None,
    company_id: int | None = None,
    company: str | None = None,
    location: str | None = None,
    work_arrangement: WorkArrangement | None = None,
    search: str | None = None,
    date_applied_from: date | None = None,
    date_applied_to: date | None = None,
    sort_by: Literal[
        "date_saved",
        "date_applied",
        "created_at",
        "job_title",
        "salary_min",
        "salary_max",
    ] = "date_saved",
    sort_order: Literal["asc", "desc"] = "desc",
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
) -> list[JobApplicationResponse]:
    """
    Return job applications using filtering, searching,
    sorting, and pagination.
    """
    return application_service.get_applications(
        db,
        status_filter=status_filter,
        company_id=company_id,
        company=company,
        location=location,
        work_arrangement=work_arrangement,
        search=search,
        date_applied_from=date_applied_from,
        date_applied_to=date_applied_to,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )


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

    WHY:
    The service layer handles the existence check and raises
    NotFoundException when the application does not exist.
    """
    return application_service.require_application_by_id(
        db,
        application_id,
    )


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

    WHY:
    The router retrieves the required resource, while the service
    layer owns company validation and duplicate URL checks.
    """
    application = application_service.require_application_by_id(
        db,
        application_id,
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
    application = application_service.require_application_by_id(
        db,
        application_id,
    )

    application_service.delete_application(
        db,
        application,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )