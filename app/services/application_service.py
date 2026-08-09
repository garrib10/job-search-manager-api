from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Company, JobApplication
from app.schemas import JobApplicationCreate, JobApplicationUpdate


def get_company_by_id(
    db: Session,
    company_id: int,
) -> Company | None:
    """
    Return a company by primary key.

    WHY:
    Job applications must reference a real company before they can
    be created or updated.
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


def create_application(
    db: Session,
    application_data: JobApplicationCreate,
) -> JobApplication:
    """
    Create and persist a new job application.

    WHY:
    Database write logic belongs in the service layer so routers stay
    focused on HTTP requests, responses, and status codes.
    """
    application = JobApplication(
        job_title=application_data.job_title,
        company_id=application_data.company_id,
        location=application_data.location,
        work_arrangement=application_data.work_arrangement,
        salary_min=application_data.salary_min,
        salary_max=application_data.salary_max,
        job_url=str(application_data.job_url),
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
) -> list[JobApplication]:
    """
    Return all job applications.

    WHY:
    For now, applications are ordered by the date they were saved,
    with the most recently saved applications first.
    """
    statement = (
        select(JobApplication)
        .order_by(
            JobApplication.date_saved.desc(),
            JobApplication.id.desc(),
        )
    )

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
    This project currently uses PUT semantics, so the editable fields
    are replaced using the complete update request.
    """
    application.job_title = application_data.job_title
    application.company_id = application_data.company_id
    application.location = application_data.location
    application.work_arrangement = application_data.work_arrangement
    application.salary_min = application_data.salary_min
    application.salary_max = application_data.salary_max
    application.job_url = str(application_data.job_url)
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

