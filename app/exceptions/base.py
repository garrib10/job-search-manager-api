class AppException(Exception):
    """
    Base exception for application-specific errors.

    WHY:
    Services should raise application exceptions without depending
    on FastAPI's HTTPException.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)