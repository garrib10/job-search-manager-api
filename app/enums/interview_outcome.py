from enum import Enum

class InterviewOutcome(str, Enum):
    """
    Represents the result of an interview round.

    WHY:
    Interview status describes whether the interview happened,
    while outcome describes what happened because of it.
    """

    PENDING = "pending"
    ADVANCED = "advanced"
    REJECTED = "rejected"
    OFFER = "offer"
    WITHDRAWN = "withdrawn"