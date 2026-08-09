from app.exceptions.base import AppException


class ConflictException(AppException):
    """
    Raised when a request conflicts with existing data.
    """

    pass