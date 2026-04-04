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
    jsonb_array_default,
)


class _Gstr2BBase(
    BigIntPrimaryKeyMixin,
    ClientForeignKeyMixin,
    StatusCodeMixin,
    UpstreamStatusCodeMixin,
    FetchedUpdatedMixin,
    Base,
):
    __abstract__ = True


class Gstr2B(_Gstr2BBase, MonthlyPeriodMixin):
    __tablename__ = "gstr2b"
    __table_args__ = (
        UniqueConstraint("client_id", "year", "month", "file_number", name="uq_gstr2b"),
        CheckConstraint(
            "response_type IN ('summary', 'documents', 'pagination_required')",
            name="ck_gstr2b_response_type",
        ),
        Index("idx_gstr2b_period", "client_id", "year", "month"),
        Index(
            "idx_gstr2b_summary_fetch",
            "client_id",
            "year",
            "month",
            postgresql_where=text("response_type = 'summary' AND file_number = ''"),
        ),
    )

    file_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    response_type: Mapped[str] = mapped_column(String(25), nullable=False)
    return_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    gen_date: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    pagination_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("FALSE"),
    )
    counterparty_summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    itc_summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    b2b: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    b2ba: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    cdnr: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    cdnra: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    isd: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    grand_summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr2BRegenStatus(_Gstr2BBase):
    __tablename__ = "gstr2b_regen_status"
    __table_args__ = (
        UniqueConstraint("client_id", "reference_id", name="uq_gstr2b_regen_status"),
    )

    reference_id: Mapped[str] = mapped_column(String(100), nullable=False)
    form_type_label: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    processing_status_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    has_errors: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    error_report: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)


Gstr2BRecord = Gstr2B
Gstr2BRegenerationStatusRecord = Gstr2BRegenStatus


__all__ = [
    "Gstr2B",
    "Gstr2BRegenStatus",
    "Gstr2BRecord",
    "Gstr2BRegenerationStatusRecord",
]
