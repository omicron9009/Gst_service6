from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import CheckConstraint, Numeric, String, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ...core.base import (
    Base,
    BigIntPrimaryKeyMixin,
    ClientForeignKeyMixin,
    FetchedUpdatedMixin,
    MonthlyPeriodMixin,
    UpstreamStatusCodeMixin,
    jsonb_array_default,
)


class _Gstr2ABase(
    BigIntPrimaryKeyMixin,
    ClientForeignKeyMixin,
    MonthlyPeriodMixin,
    UpstreamStatusCodeMixin,
    FetchedUpdatedMixin,
    Base,
):
    __abstract__ = True


class Gstr2AB2B(_Gstr2ABase):
    __tablename__ = "gstr2a_b2b"
    __table_args__ = (
        UniqueConstraint("client_id", "year", "month", name="uq_gstr2a_b2b"),
        Index("idx_gstr2a_b2b_period", "client_id", "year", "month"),
    )

    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr2AB2BA(_Gstr2ABase):
    __tablename__ = "gstr2a_b2ba"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "year",
            "month",
            "filter_counterparty_gstin",
            name="uq_gstr2a_b2ba",
        ),
        CheckConstraint(
            "filter_counterparty_gstin = '' OR LENGTH(filter_counterparty_gstin) = 15",
            name="ck_gstr2a_b2ba_counterparty_len",
        ),
    )

    filter_counterparty_gstin: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr2ACDN(_Gstr2ABase):
    __tablename__ = "gstr2a_cdn"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "year",
            "month",
            "filter_counterparty_gstin",
            "filter_from_date",
            name="uq_gstr2a_cdn",
        ),
        CheckConstraint(
            "filter_counterparty_gstin = '' OR LENGTH(filter_counterparty_gstin) = 15",
            name="ck_gstr2a_cdn_counterparty_len",
        ),
        Index("idx_gstr2a_cdn_period", "client_id", "year", "month"),
    )

    filter_counterparty_gstin: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    filter_from_date: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr2ACDNA(_Gstr2ABase):
    __tablename__ = "gstr2a_cdna"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "year",
            "month",
            "filter_counterparty_gstin",
            name="uq_gstr2a_cdna",
        ),
        CheckConstraint(
            "filter_counterparty_gstin = '' OR LENGTH(filter_counterparty_gstin) = 15",
            name="ck_gstr2a_cdna_counterparty_len",
        ),
    )

    filter_counterparty_gstin: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr2ADocument(_Gstr2ABase):
    __tablename__ = "gstr2a_document"
    __table_args__ = (UniqueConstraint("client_id", "year", "month", name="uq_gstr2a_document"),)

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
    summary_all: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    summary_pending_action: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)


class Gstr2AISD(_Gstr2ABase):
    __tablename__ = "gstr2a_isd"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "year",
            "month",
            "filter_counterparty_gstin",
            name="uq_gstr2a_isd",
        ),
        CheckConstraint(
            "filter_counterparty_gstin = '' OR LENGTH(filter_counterparty_gstin) = 15",
            name="ck_gstr2a_isd_counterparty_len",
        ),
    )

    filter_counterparty_gstin: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr2ATDS(_Gstr2ABase):
    __tablename__ = "gstr2a_tds"
    __table_args__ = (UniqueConstraint("client_id", "year", "month", name="uq_gstr2a_tds"),)

    entry_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    grand_total_deduction_base: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    grand_total_igst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    grand_total_cgst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    grand_total_sgst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    grand_total_tds_credit: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    tds_entries: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


Gstr2AB2BRecord = Gstr2AB2B
Gstr2AB2BARecord = Gstr2AB2BA
Gstr2ACDNRecord = Gstr2ACDN
Gstr2ACDNARecord = Gstr2ACDNA
Gstr2ADocumentRecord = Gstr2ADocument
Gstr2AISDRecord = Gstr2AISD
Gstr2ATDSRecord = Gstr2ATDS


__all__ = [
    "Gstr2AB2B",
    "Gstr2AB2BA",
    "Gstr2ACDN",
    "Gstr2ACDNA",
    "Gstr2ADocument",
    "Gstr2AISD",
    "Gstr2ATDS",
    "Gstr2AB2BRecord",
    "Gstr2AB2BARecord",
    "Gstr2ACDNRecord",
    "Gstr2ACDNARecord",
    "Gstr2ADocumentRecord",
    "Gstr2AISDRecord",
    "Gstr2ATDSRecord",
]
