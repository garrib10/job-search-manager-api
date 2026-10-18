from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.db_types import UTCDateTime

if TYPE_CHECKING:
    from app.models.application import JobApplication
    from app.models.company import Company

class User(Base):
    """
    Application user account.

    WHY:
    Users authenticate with an email address and password.
    Passwords are never stored in plain text—only securely
    hashed passwords are persisted.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    companies: Mapped[list["Company"]] = relationship(
        back_populates="user",
    )

    applications: Mapped[list["JobApplication"]] = relationship(
        back_populates="user",
    )
