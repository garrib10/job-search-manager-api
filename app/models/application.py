from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.enums import ApplicationStatus, WorkArrangement

if TYPE_CHECKING:
    from app.models.company import Company


class JobApplication(Base):
    """
    Represents a single job application.

    WHY:
    Each JobApplication belongs to exactly one Company and stores
    job-specific information such as status, salary range, work
    arrangement, application dates, and notes.
    """

    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    job_title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
    )

    work_arrangement: Mapped[WorkArrangement | None] = mapped_column(
        Enum(
            WorkArrangement,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=True,
        index=True,
    )

    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(
            ApplicationStatus,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=ApplicationStatus.SAVED,
        index=True,
    )

    salary_min: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    salary_max: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    job_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    date_saved: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=date.today,
    )

    date_applied: Mapped[date | None] = mapped_column(
        Date,
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

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    company: Mapped["Company"] = relationship(
        back_populates="applications",
    )

