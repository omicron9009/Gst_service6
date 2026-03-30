from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Boolean, CheckConstraint, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ...core.base import (
    Base,
    BigIntPrimaryKeyMixin,
    ClientForeignKeyMixin,
    FetchedUpdatedMixin,
    MonthlyPeriodMixin,
    StatusCodeMixin,
    UpstreamStatusCodeMixin,
)


class GstReturnStatus(
    BigIntPrimaryKeyMixin,
    ClientForeignKeyMixin,
    MonthlyPeriodMixin,
    StatusCodeMixin,
    UpstreamStatusCodeMixin,
    FetchedUpdatedMixin,
    Base,
):
    __tablename__ = "gst_return_status"
    __table_args__ = (
        UniqueConstraint("client_id", "year", "month", "reference_id", name="uq_gst_return_status"),
        CheckConstraint(
            "processing_status IS NULL OR processing_status IN ('P', 'PE', 'ER', 'REC')",
            name="ck_gst_return_status_processing",
        ),
        Index("idx_gst_return_status_period", "client_id", "year", "month"),
        Index("idx_gst_return_status_ref", "client_id", "reference_id"),
        Index(
            "idx_gst_return_status_errors",
            "client_id",
            "year",
            "month",
            postgresql_where=text("has_errors = TRUE"),
        ),
    )

    reference_id: Mapped[str] = mapped_column(String(100), nullable=False)
    form_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    form_type_label: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    action: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    processing_status: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    processing_status_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    has_errors: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    error_report: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)


GstReturnStatusRecord = GstReturnStatus


__all__ = ["GstReturnStatus", "GstReturnStatusRecord"]
