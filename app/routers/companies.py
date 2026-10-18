from typing import Annotated
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import CompanyCreate, CompanyResponse, CompanyUpdate
from app.routers.auth import CurrentUser, get_current_user
from app.services import company_service

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
    # WHY:
    # Every endpoint in this router requires a valid bearer token. Each
    # endpoint also takes CurrentUser so the service can scope records to
    # the logged-in user; this router-level dependency keeps any new
    # endpoint protected by default.
    dependencies=[Depends(get_current_user)],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a company",
)
def create_company(
    company_data: CompanyCreate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> CompanyResponse:
    """
    Create a new company owned by the authenticated user.

    WHY:
    The router handles HTTP concerns while the service layer handles
    persistence and business logic. The owner always comes from the
    bearer token, never from the request body.
    """
    return company_service.create_company(
        db,
        company_data,
        user_id=current_user.id,
    )


@router.get(
    "",
    response_model=list[CompanyResponse],
    summary="List companies",
)
def get_companies(
    db: DatabaseSession,
    current_user: CurrentUser,
) -> list[CompanyResponse]:
    """Return the authenticated user's companies."""

    return company_service.get_companies(
        db,
        user_id=current_user.id,
    )


@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    summary="Get a company",
)
def get_company(
    company_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> CompanyResponse:
    """
    Return one company by ID.

    WHY:
    The service layer owns the existence check. If the company does
    not exist, it raises NotFoundException and the global handler
    converts that exception into a 404 response.
    """
    return company_service.require_company_by_id(
        db,
        company_id,
        user_id=current_user.id,
    )


@router.put(
    "/{company_id}",
    response_model=CompanyResponse,
    summary="Update a company",
)
def update_company(
    company_id: int,
    company_data: CompanyUpdate,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> CompanyResponse:
    """Update an existing company."""

    company = company_service.require_company_by_id(
        db,
        company_id,
        user_id=current_user.id,
    )

    return company_service.update_company(
        db,
        company,
        company_data,
    )


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a company",
)
def delete_company(
    company_id: int,
    db: DatabaseSession,
    current_user: CurrentUser,
) -> Response:
    """Delete an existing company."""

    company = company_service.require_company_by_id(
        db,
        company_id,
        user_id=current_user.id,
    )

    company_service.delete_company(
        db,
        company,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
    )
