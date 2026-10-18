from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import commit_or_rollback
from app.exceptions import ConflictException, NotFoundException
from app.models import Company, JobApplication
from app.schemas import CompanyCreate, CompanyUpdate

def create_company(
    db: Session,
    company_data: CompanyCreate,
    *,
    user_id: int,
) -> Company:
    """
    Create and persist a new company.

    WHY:
    Database write logic belongs in the service layer so routers can stay
    focused on HTTP concerns like requests, responses, and status codes.
    """
    company = Company(
        name=company_data.name,
        website=str(company_data.website) if company_data.website else None,
        industry=company_data.industry,
        location=company_data.location,
        notes=company_data.notes,
        user_id=user_id,
    )

    db.add(company)
    commit_or_rollback(db)
    db.refresh(company)

    return company


def get_companies(
    db: Session,
    *,
    user_id: int,
) -> list[Company]:
    """Return the user's companies ordered alphabetically by name."""

    statement = (
        select(Company)
        .where(Company.user_id == user_id)
        .order_by(Company.name)
    )

    return list(db.scalars(statement).all())


def require_company_by_id(
    db: Session,
    company_id: int,
    *,
    user_id: int,
) -> Company:
    """
    Return one of the user's companies or raise a not-found error.

    WHY:
    Database-dependent existence checks belong in the service layer.
    Another user's company is reported exactly like a missing one, so
    the API never reveals which IDs exist. The global exception handler
    converts this exception into a consistent 404 response.
    """
    company = db.scalar(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == user_id,
        )
    )

    if company is None:
        raise NotFoundException("Company not found")

    return company


def update_company(
    db: Session,
    company: Company,
    company_data: CompanyUpdate,
) -> Company:
    """Update the editable fields of an existing company."""

    company.name = company_data.name
    company.website = (
        str(company_data.website)
        if company_data.website
        else None
    )
    company.industry = company_data.industry
    company.location = company_data.location
    company.notes = company_data.notes

    commit_or_rollback(db)
    db.refresh(company)

    return company


def company_has_applications(
    db: Session,
    company_id: int,
) -> bool:
    """Return True if any job application is filed under the company."""
    return db.scalar(
        select(JobApplication.id)
        .where(JobApplication.company_id == company_id)
        .limit(1)
    ) is not None


def delete_company(
    db: Session,
    company: Company,
) -> None:
    """
    Delete a company that has no job applications.

    WHY:
    Deleting a company must not silently delete the applications filed
    under it. The user has to delete or move those applications first. The
    foreign key from job_applications also blocks the delete in the
    database, so a concurrent request that adds an application still ends
    in a 409 rather than orphaned data.
    """
    if company_has_applications(db, company.id):
        raise ConflictException(
            "Company has job applications. Delete or move them first."
        )

    db.delete(company)
    commit_or_rollback(db)
