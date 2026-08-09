from sqlalchemy import select
from sqlalchemy.orm import Session
from app.exceptions import NotFoundException
from app.models import Company
from app.schemas import CompanyCreate, CompanyUpdate

def create_company(
    db: Session,
    company_data: CompanyCreate,
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
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    return company


def get_companies(
    db: Session,
) -> list[Company]:
    """Return all companies ordered alphabetically by name."""

    statement = select(Company).order_by(Company.name)

    return list(db.scalars(statement).all())


def get_company_by_id(
    db: Session,
    company_id: int,
) -> Company | None:
    """Return one company, or None when the ID does not exist."""

    return db.get(Company, company_id)


def require_company_by_id(
    db: Session,
    company_id: int,
) -> Company:
    """
    Return one company or raise an application-level not-found error.

    WHY:
    Database-dependent existence checks belong in the service layer.
    The global exception handler converts this exception into a
    consistent 404 response.
    """
    company = db.get(Company, company_id)

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

    db.commit()
    db.refresh(company)

    return company


def delete_company(
    db: Session,
    company: Company,
) -> None:
    """Delete an existing company."""

    db.delete(company)
    db.commit()
