from fastapi import FastAPI
from app.config import get_settings
from app.database import Base, engine
from app.models import Company, Interview, JobApplication
from app.routers.companies import router as companies_router
from app.schemas.health import HealthResponse
from app.routers.applications import router as applications_router
from app.routers.interviews import router as interviews_router

settings = get_settings()

# WHY:
# Importing Company registers its table metadata with SQLAlchemy's Base.
# create_all() then creates any missing tables in the configured database.
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title=settings.app_name,
    description=(
        "A REST API for managing companies, job applications, "
        "interviews, follow-ups, and job-search priorities."
    ),
    version=settings.app_version,
)

# WHY:
# Routers keep endpoint definitions organized by resource instead of
# placing every API route directly inside main.py.
app.include_router(companies_router)
app.include_router(applications_router)
app.include_router(interviews_router)

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Check API health",
)
def get_health() -> HealthResponse:
    """
    Confirm that the API process is running and accepting requests.

    Deployment platforms and monitoring services can use this endpoint
    to determine whether the application is reachable.
    """
    return HealthResponse(
        status="ok",
        application=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )

