from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from app.models.application import JobApplication
    from app.models.user import User



class Company(Base):
    """
    Database representation of an employer.

    WHY:
    Company information is stored separately from job applications so
    multiple applications can reference the same employer without
    duplicating company-level data.
    """

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        index=True,
    )

    website: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    industry: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # WHY:
    # Every company belongs to the user who created it. The constraint is
    # named so migrations can drop or alter it reliably.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="fk_companies_user_id_users"),
        nullable=False,
        index=True,
    )

    user: Mapped["User"] = relationship(
        back_populates="companies",
    )

    applications: Mapped[list["JobApplication"]] = relationship(
    back_populates="company",
)