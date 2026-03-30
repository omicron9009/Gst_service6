from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import CheckConstraint, Index, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ...core.base import (
    Base,
    BigIntPrimaryKeyMixin,
    ClientForeignKeyMixin,
    FetchedUpdatedMixin,
    FinancialYearMixin,
    LargeAmount,
    StatusCodeMixin,
    UpstreamStatusCodeMixin,
    jsonb_array_default,
    jsonb_object_default,
)


class _Gstr9Base(
    BigIntPrimaryKeyMixin,
    ClientForeignKeyMixin,
    FinancialYearMixin,
    StatusCodeMixin,
    UpstreamStatusCodeMixin,
    FetchedUpdatedMixin,
    Base,
):
    __abstract__ = True


class Gstr9AutoCalculated(_Gstr9Base):
    __tablename__ = "gstr9_auto_calculated"
    __table_args__ = (
        UniqueConstraint("client_id", "financial_year", name="uq_gstr9_auto_calculated"),
        CheckConstraint(
            r"financial_year ~ '^\d{4}-\d{2}$'",
            name="ck_gstr9_auto_fy_format",
        ),
        Index("idx_gstr9_auto_fy", "client_id", "financial_year"),
    )

    financial_period: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    aggregate_turnover: Mapped[Optional[float]] = mapped_column(LargeAmount, nullable=True)
    hsn_min_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    table4_outward_supplies: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    table5_exempt_nil_non_gst: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    table6_itc_availed: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    table8_itc_as_per_2b: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    table9_tax_paid: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)


class Gstr9Table8A(_Gstr9Base):
    __tablename__ = "gstr9_table8a"
    __table_args__ = (
        UniqueConstraint("client_id", "financial_year", "file_number", name="uq_gstr9_table8a"),
        CheckConstraint(
            r"financial_year ~ '^\d{4}-\d{2}$'",
            name="ck_gstr9_table8a_fy_format",
        ),
        Index("idx_gstr9_table8a_fy", "client_id", "financial_year"),
    )

    file_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    b2b: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )
    b2ba: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )
    cdn: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )
    summary_b2b_taxable_value: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    summary_b2b_igst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    summary_b2b_cgst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    summary_b2b_sgst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    summary_b2b_cess: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    summary_b2b_invoice_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Gstr9Details(_Gstr9Base):
    __tablename__ = "gstr9_details"
    __table_args__ = (
        UniqueConstraint("client_id", "financial_year", name="uq_gstr9_details"),
        CheckConstraint(
            r"financial_year ~ '^\d{4}-\d{2}$'",
            name="ck_gstr9_details_fy_format",
        ),
    )

    detail_sections: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=jsonb_object_default(),
    )


Gstr9AutoCalculatedRecord = Gstr9AutoCalculated
Gstr9Table8ARecord = Gstr9Table8A
Gstr9DetailsRecord = Gstr9Details


__all__ = [
    "Gstr9AutoCalculated",
    "Gstr9Table8A",
    "Gstr9Details",
    "Gstr9AutoCalculatedRecord",
    "Gstr9Table8ARecord",
    "Gstr9DetailsRecord",
]
