from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.enums import (
    InterviewOutcome,
    InterviewStatus,
    InterviewType,
)

if TYPE_CHECKING:
    from app.models.application import JobApplication


class Interview(Base):
    """
    Represents a single interview for a job application.

    WHY:
    A JobApplication may have multiple interviews throughout
    the hiring process. Each Interview stores the interview
    details, scheduling information, and outcome.
    """

    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    interview_type: Mapped[InterviewType] = mapped_column(
        Enum(
            InterviewType,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[InterviewStatus] = mapped_column(
        Enum(
            InterviewStatus,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=InterviewStatus.SCHEDULED,
        index=True,
    )

    outcome: Mapped[InterviewOutcome] = mapped_column(
        Enum(
            InterviewOutcome,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=InterviewOutcome.PENDING,
        index=True,
    )

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    interviewer: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    application_id: Mapped[int] = mapped_column(
        ForeignKey("job_applications.id"),
        nullable=False,
        index=True,
    )

    application: Mapped["JobApplication"] = relationship(
        back_populates="interviews",
    )