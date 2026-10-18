import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from app.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)

async def not_found_exception_handler(
    request: Request,
    exc: NotFoundException,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "detail": exc.message,
        },
    )

async def conflict_exception_handler(
    request: Request,
    exc: ConflictException,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": exc.message,
        },
    )

async def validation_exception_handler(
    request: Request,
    exc: ValidationException,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": exc.message,
        },
    )

logger = logging.getLogger(__name__)

INTEGRITY_ERROR_DETAIL = "The request conflicts with existing data."


async def integrity_error_exception_handler(
    request: Request,
    exc: IntegrityError,
) -> JSONResponse:
    """
    Turn a database constraint violation into a generic 409 response.

    WHY:
    Services check for duplicates and missing references before writing,
    but two concurrent requests can still both pass those checks and then
    collide on a unique or foreign key constraint. The database error names
    tables, columns, constraints, and sometimes the submitted values, so it
    is logged server-side only and the client gets a generic message. The
    session has already been rolled back by commit_or_rollback().
    """
    logger.warning(
        "Database integrity error on %s %s: %s",
        request.method,
        request.url.path,
        exc.orig,
    )

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "detail": INTEGRITY_ERROR_DETAIL,
        },
    )
