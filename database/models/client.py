from __future__ import annotations

from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.base import Base, PrimaryKeyMixin, TimestampMixin


class Client(PrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "clients"

    gstin: Mapped[str] = mapped_column(String(15), nullable=False, unique=True, index=True)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    sessions = relationship(
        "GstSession",
        back_populates="client",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

