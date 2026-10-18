from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """
    A DATETIME column that always stores UTC and always returns UTC-aware values.

    WHY:
    MySQL DATETIME has no time zone. Without this, PyMySQL writes an
    offset-aware datetime's wall-clock time and drops the offset (10:00-05:00
    was stored as 10:00), and values come back naive with no indication of
    their zone. Aware values are converted to UTC before they are stored, and
    every value read back is marked as UTC.

    Naive values are treated as already being UTC. API input never produces
    them (it requires an offset); they only come from internal code.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)

        return value

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is not None:
            value = value.replace(tzinfo=timezone.utc)

        return value
