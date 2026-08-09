from fastapi import Request, status
from fastapi.responses import JSONResponse
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