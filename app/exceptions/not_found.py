from app.exceptions.base import AppException


class NotFoundException(AppException):
    """
    Raised when a requested resource cannot be found.
    """

    pass