"""
Reusable validated field types for request schemas.
"""

from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, AwareDatetime, Field, StringConstraints

# MySQL TEXT holds at most 65,535 bytes. With utf8mb4 a character takes 1 to 4
# bytes, so the limit is checked on the UTF-8 encoded size, not the number of
# characters.
MYSQL_TEXT_MAX_BYTES = 65_535


def to_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


def within_text_byte_limit(value: str) -> str:
    if len(value.encode("utf-8")) > MYSQL_TEXT_MAX_BYTES:
        raise ValueError(
            f"must be at most {MYSQL_TEXT_MAX_BYTES:,} bytes when encoded as UTF-8 "
            "(about 65,000 plain characters, or fewer if it contains accented letters or emoji)"
        )

    return value


# WHY:
# Datetimes must include a UTC offset ("Z" or "+02:00"). A naive value is
# ambiguous, so it is rejected instead of guessed. Accepted values are
# converted to UTC.
UtcDatetime = Annotated[
    AwareDatetime,
    AfterValidator(to_utc),
    Field(description="ISO 8601 date and time with a UTC offset, for example 2026-11-02T15:00:00Z. Returned in UTC."),
]


def RequiredText(max_length: int):  # noqa: N802 (used like a type)
    """A required string with surrounding whitespace removed; blank values are rejected."""
    return Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=max_length)]


NotesText = Annotated[
    str,
    Field(description="Free text, at most 65,535 bytes when encoded as UTF-8."),
    AfterValidator(within_text_byte_limit),
]
