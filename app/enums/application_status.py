from enum import Enum


class ApplicationStatus(str, Enum):
    """
    Represents the current stage of a job application.

    WHY:
    Using an Enum prevents inconsistent status values from being
    stored in the database or accepted by the API.
    """

    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"