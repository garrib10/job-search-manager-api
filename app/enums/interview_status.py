from enum import Enum

class InterviewStatus(str, Enum):
    """
    Represents the current scheduling state of an interview.
    """

    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"