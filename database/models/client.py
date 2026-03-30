from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, CHAR, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.base import Base, BigIntPrimaryKeyMixin, CreatedUpdatedMixin


class Client(BigIntPrimaryKeyMixin, CreatedUpdatedMixin, Base):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("gstin", name="uq_clients_gstin"),
        CheckConstraint("LENGTH(TRIM(gstin)) = 15", name="ck_clients_gstin_length"),
        {"comment": "Each GST taxpayer client managed by the CA firm."},
    )

    gstin: Mapped[str] = mapped_column(
        CHAR(15),
        nullable=False,
        comment="Goods and Services Tax Identification Number - exactly 15 chars.",
    )
    username: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="GST portal username associated with this GSTIN.",
    )
    trade_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    legal_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("TRUE"),
    )

    sessions = relationship("ClientSession", back_populates="client")
    otp_requests = relationship("OtpRequest", back_populates="client")

