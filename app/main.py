from fastapi import FastAPI

from app.config import get_settings
from app.schemas.health import HealthResponse


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "A REST API for managing companies, job applications, "
        "interviews, follow-ups, and job-search priorities."
    ),
    version=settings.app_version,
)


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