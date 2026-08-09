from enum import Enum


class WorkArrangement(str, Enum):
    """
    Represents where the job is performed.

    WHY:
    Restricting work arrangements to known values prevents inconsistent
    data from being stored in the database or accepted by the API.
    """

    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"