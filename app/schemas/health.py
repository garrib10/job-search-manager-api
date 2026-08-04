from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Public response returned by the API health endpoint."""

    status: str
    application: str
    version: str
    environment: str