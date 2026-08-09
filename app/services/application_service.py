from datetime import date
from typing import Literal
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from app.enums import ApplicationStatus, WorkArrangement
from app.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.models import Company, JobApplication
from app.schemas import JobApplicationCreate, JobApplicationUpdate

def get_company_by_id(
    db: Session,
    company_id: int,
) -> Company | None:
    """
    Return a company by primary key.

    WHY:
    Nullable lookup helpers are still useful in cases where the caller
    may want to inspect whether a company exists without immediately
    treating the absence as an error.
    """
    return db.get(Company, company_id)


def get_application_by_job_url(
    db: Session,
    job_url: str,
) -> JobApplication | None:
    """
    Return a job application matching an exact job URL.

    WHY:
    The project treats a job URL as unique so the same posting is not
    accidentally tracked more than once.
    """
    statement = select(JobApplication).where(
        JobApplication.job_url == job_url
    )

    return db.scalar(statement)

def require_application_by_id(
    db: Session,
    application_id: int,
) -> JobApplication:
    """
    Return a job application or raise a not-found exception.

    WHY:
    Database-dependent existence checks belong in the service layer.
    The global exception handler converts this exception into a
    consistent 404 HTTP response.
    """
    application = db.get(JobApplication, application_id)

    if application is None:
        raise NotFoundException("Job application not found")

    return application


def create_application(
    db: Session,
    application_data: JobApplicationCreate,
) -> JobApplication:
    """
    Create and persist a new job application.

    WHY:
    The service layer owns database-dependent business rules such as
    validating the referenced company and preventing duplicate job URLs.
    """
    company = db.get(
        Company,
        application_data.company_id,
    )

    if company is None:
        raise NotFoundException("Company not found")

    job_url = str(application_data.job_url)

    existing_application = get_application_by_job_url(
        db,
        job_url,
    )

    if existing_application is not None:
        raise ConflictException(
            "An application with this job URL already exists"
        )

    application = JobApplication(
        job_title=application_data.job_title,
        company_id=application_data.company_id,
        location=application_data.location,
        work_arrangement=application_data.work_arrangement,
        salary_min=application_data.salary_min,
        salary_max=application_data.salary_max,
        job_url=job_url,
        status=application_data.status,
        notes=application_data.notes,
        date_applied=application_data.date_applied,
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    return application


def get_applications(
    db: Session,
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
    limit: int = 20,
    offset: int = 0,
) -> list[JobApplication]:
    """
    Return job applications using optional filtering, searching,
    sorting, and pagination.

    WHY:
    Building the query conditionally lets the API combine multiple
    optional filters without creating separate endpoints for every
    possible search combination.
    """

    if (
        date_applied_from is not None
        and date_applied_to is not None
        and date_applied_from > date_applied_to
    ):
        raise ValidationException(
            "date_applied_from cannot be after date_applied_to"
        )

    statement = select(JobApplication)

    if status_filter is not None:
        statement = statement.where(
            JobApplication.status == status_filter
        )

    if company_id is not None:
        statement = statement.where(
            JobApplication.company_id == company_id
        )

    if company:
        statement = statement.join(JobApplication.company).where(
            Company.name.ilike(f"%{company}%")
        )

    if location:
        statement = statement.where(
            JobApplication.location.ilike(f"%{location}%")
        )

    if work_arrangement is not None:
        statement = statement.where(
            JobApplication.work_arrangement == work_arrangement
        )

    if search:
        search_pattern = f"%{search}%"

        statement = statement.where(
            or_(
                JobApplication.job_title.ilike(search_pattern),
                JobApplication.location.ilike(search_pattern),
                JobApplication.notes.ilike(search_pattern),
            )
        )

    if date_applied_from is not None:
        statement = statement.where(
            JobApplication.date_applied >= date_applied_from
        )

    if date_applied_to is not None:
        statement = statement.where(
            JobApplication.date_applied <= date_applied_to
        )

    sort_columns = {
        "date_saved": JobApplication.date_saved,
        "date_applied": JobApplication.date_applied,
        "created_at": JobApplication.created_at,
        "job_title": JobApplication.job_title,
        "salary_min": JobApplication.salary_min,
        "salary_max": JobApplication.salary_max,
    }

    sort_column = sort_columns[sort_by]

    if sort_order == "asc":
        statement = statement.order_by(
            sort_column.asc(),
            JobApplication.id.asc(),
        )
    else:
        statement = statement.order_by(
            sort_column.desc(),
            JobApplication.id.desc(),
        )

    statement = statement.limit(limit).offset(offset)

    return list(db.scalars(statement).all())


def get_application_by_id(
    db: Session,
    application_id: int,
) -> JobApplication | None:
    """Return one job application by primary key."""
    return db.get(JobApplication, application_id)


def update_application(
    db: Session,
    application: JobApplication,
    application_data: JobApplicationUpdate,
) -> JobApplication:
    """
    Update an existing job application.

    WHY:
    The service validates database-dependent business rules before
    applying the PUT update.
    """
    company = db.get(
        Company,
        application_data.company_id,
    )

    if company is None:
        raise NotFoundException("Company not found")

    job_url = str(application_data.job_url)

    existing_application = get_application_by_job_url(
        db,
        job_url,
    )

    if (
        existing_application is not None
        and existing_application.id != application.id
    ):
        raise ConflictException(
            "An application with this job URL already exists"
        )

    application.job_title = application_data.job_title
    application.company_id = application_data.company_id
    application.location = application_data.location
    application.work_arrangement = application_data.work_arrangement
    application.salary_min = application_data.salary_min
    application.salary_max = application_data.salary_max
    application.job_url = job_url
    application.status = application_data.status
    application.notes = application_data.notes
    application.date_applied = application_data.date_applied

    db.commit()
    db.refresh(application)

    return application


def delete_application(
    db: Session,
    application: JobApplication,
) -> None:
    """Delete an existing job application."""

    db.delete(application)
    db.commit()