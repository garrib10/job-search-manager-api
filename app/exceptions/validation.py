from app.exceptions.base import AppException


class ValidationException(AppException):
    """
    Raised when a business rule is violated.
    """

    pass