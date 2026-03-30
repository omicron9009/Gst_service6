from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.base import Base, BigIntPrimaryKeyMixin, ClientForeignKeyMixin, CreatedUpdatedMixin


class ClientSession(BigIntPrimaryKeyMixin, ClientForeignKeyMixin, CreatedUpdatedMixin, Base):
    __tablename__ = "client_sessions"
    __table_args__ = (
        Index(
            "uq_client_sessions_one_active",
            "client_id",
            unique=True,
            postgresql_where=text("is_active = TRUE"),
        ),
        Index("idx_client_sessions_client_id", "client_id"),
        Index(
            "idx_client_sessions_expiry_active",
            "session_expiry",
            postgresql_where=text("is_active = TRUE"),
        ),
        {
            "comment": (
                "OTP-verified session tokens per client. At most one row with "
                "is_active=TRUE per client."
            )
        },
    )

    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    session_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("TRUE"),
        comment="FALSE = deactivated (session expired or replaced). TRUE = currently valid.",
    )

    client = relationship("Client", back_populates="sessions")


class OtpRequest(BigIntPrimaryKeyMixin, ClientForeignKeyMixin, Base):
    __tablename__ = "otp_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'verified', 'expired', 'failed')",
            name="ck_otp_requests_status",
        ),
        Index("idx_otp_requests_client_id", "client_id"),
        {"comment": "Audit log of all OTP generation and verification attempts per client."},
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    upstream_status_cd: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    client = relationship("Client", back_populates="otp_requests")


GstSession = ClientSession
