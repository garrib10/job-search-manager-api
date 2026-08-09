from enum import Enum

class InterviewType(str, Enum):
    """
    Represents the type of interview being conducted.

    WHY:
    Using an Enum keeps interview types consistent across
    the API, service layer, and database.
    """

    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    HIRING_MANAGER = "hiring_manager"
    ONSITE = "onsite"
    VIRTUAL_ONSITE = "virtual_onsite"
    FINAL = "final"
    HR = "hr"
    OTHER = "other"