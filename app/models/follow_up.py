from datetime import date, datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Date, ForeignKey, String, func, false
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.db_types import UTCDateTime

if TYPE_CHECKING:
    from app.models.application import JobApplication


class FollowUp(Base):
    """
    A to-do attached to a job application, such as "Email the recruiter".

    WHY:
    Follow-ups belong to whoever owns their job application, like interviews,
    so they have no user_id of their own. The due value is a calendar date
    because follow-ups are planned by day, matching date_applied and
    date_saved.
    """

    __tablename__ = "follow_ups"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
    )

    # WHY:
    # Set by the server when a follow-up is completed and cleared when it is
    # reopened; clients only send the completed flag.
    completed_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # WHY:
    # Deleting an application deletes its follow-ups, the same rule as its
    # interviews. The constraint is named so migrations can manage it.
    application_id: Mapped[int] = mapped_column(
        ForeignKey(
            "job_applications.id",
            name="fk_follow_ups_application_id_job_applications",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    application: Mapped["JobApplication"] = relationship(
        back_populates="follow_ups",
    )
