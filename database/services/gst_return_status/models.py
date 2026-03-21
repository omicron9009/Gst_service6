from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ...core.base import (
    Base,
    ClientScopeMixin,
    MonthlyPeriodMixin,
    PrimaryKeyMixin,
    RawPayloadMixin,
    TimestampMixin,
)


class GstReturnStatusRecord(
    PrimaryKeyMixin,
    ClientScopeMixin,
    MonthlyPeriodMixin,
    RawPayloadMixin,
    TimestampMixin,
    Base,
):
    __tablename__ = "gst_return_status_records"

    reference_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status_cd: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    form_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    form_type_label: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    action: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    processing_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    processing_status_label: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    has_errors: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_report: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


__all__ = ["GstReturnStatusRecord"]

