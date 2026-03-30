from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import CheckConstraint, Index, Numeric, String, UniqueConstraint, text
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


class _Gstr1Base(
    BigIntPrimaryKeyMixin,
    ClientForeignKeyMixin,
    MonthlyPeriodMixin,
    UpstreamStatusCodeMixin,
    FetchedUpdatedMixin,
    Base,
):
    __abstract__ = True


class Gstr1AdvanceTax(_Gstr1Base):
    __tablename__ = "gstr1_advance_tax"
    __table_args__ = (
        UniqueConstraint("client_id", "year", "month", name="uq_gstr1_advance_tax"),
        Index("idx_gstr1_at_period", "client_id", "year", "month"),
    )

    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr1B2B(_Gstr1Base):
    __tablename__ = "gstr1_b2b"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "year",
            "month",
            "filter_action_required",
            "filter_from_date",
            "filter_counterparty_gstin",
            name="uq_gstr1_b2b",
        ),
        CheckConstraint(
            "filter_action_required IN ('', 'Y', 'N')",
            name="ck_gstr1_b2b_action_required",
        ),
        CheckConstraint(
            "filter_counterparty_gstin = '' OR LENGTH(filter_counterparty_gstin) = 15",
            name="ck_gstr1_b2b_counterparty_gstin_len",
        ),
        Index("idx_gstr1_b2b_period", "client_id", "year", "month"),
        Index(
            "idx_gstr1_b2b_base_fetch",
            "client_id",
            "year",
            "month",
            postgresql_where=text(
                "filter_action_required = '' "
                "AND filter_from_date = '' "
                "AND filter_counterparty_gstin = ''"
            ),
        ),
    )

    filter_action_required: Mapped[str] = mapped_column(
        String(1),
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
    filter_counterparty_gstin: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    total_invoices: Mapped[Optional[int]] = mapped_column(nullable=True)
    total_taxable_value: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    total_cgst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    total_sgst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    total_igst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    invoices: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr1Summary(_Gstr1Base):
    __tablename__ = "gstr1_summary"
    __table_args__ = (
        UniqueConstraint("client_id", "year", "month", "summary_type", name="uq_gstr1_summary"),
        CheckConstraint("summary_type IN ('short', 'long')", name="ck_gstr1_summary_type"),
        Index("idx_gstr1_summary_period", "client_id", "year", "month"),
    )

    summary_type: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        default="short",
        server_default=text("'short'"),
    )
    ret_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    sections: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr1B2CSA(_Gstr1Base):
    __tablename__ = "gstr1_b2csa"
    __table_args__ = (UniqueConstraint("client_id", "year", "month", name="uq_gstr1_b2csa"),)

    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr1B2CS(_Gstr1Base):
    __tablename__ = "gstr1_b2cs"
    __table_args__ = (UniqueConstraint("client_id", "year", "month", name="uq_gstr1_b2cs"),)

    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr1CDNR(_Gstr1Base):
    __tablename__ = "gstr1_cdnr"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "year",
            "month",
            "filter_action_required",
            "filter_from_date",
            name="uq_gstr1_cdnr",
        ),
        CheckConstraint(
            "filter_action_required IN ('', 'Y', 'N')",
            name="ck_gstr1_cdnr_action",
        ),
        Index("idx_gstr1_cdnr_period", "client_id", "year", "month"),
    )

    filter_action_required: Mapped[str] = mapped_column(
        String(1),
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
    record_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr1DocIssue(_Gstr1Base):
    __tablename__ = "gstr1_doc_issue"
    __table_args__ = (UniqueConstraint("client_id", "year", "month", name="uq_gstr1_doc_issue"),)

    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr1HSN(_Gstr1Base):
    __tablename__ = "gstr1_hsn"
    __table_args__ = (UniqueConstraint("client_id", "year", "month", name="uq_gstr1_hsn"),)

    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr1Nil(_Gstr1Base):
    __tablename__ = "gstr1_nil"
    __table_args__ = (UniqueConstraint("client_id", "year", "month", name="uq_gstr1_nil"),)

    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr1B2CL(_Gstr1Base):
    __tablename__ = "gstr1_b2cl"
    __table_args__ = (UniqueConstraint("client_id", "year", "month", name="uq_gstr1_b2cl"),)

    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr1CDNUR(_Gstr1Base):
    __tablename__ = "gstr1_cdnur"
    __table_args__ = (UniqueConstraint("client_id", "year", "month", name="uq_gstr1_cdnur"),)

    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr1EXP(_Gstr1Base):
    __tablename__ = "gstr1_exp"
    __table_args__ = (UniqueConstraint("client_id", "year", "month", name="uq_gstr1_exp"),)

    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class Gstr1TXP(_Gstr1Base):
    __tablename__ = "gstr1_txp"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "year",
            "month",
            "filter_counterparty_gstin",
            "filter_action_required",
            "filter_from_date",
            name="uq_gstr1_txp",
        ),
        CheckConstraint(
            "filter_action_required IN ('', 'Y', 'N')",
            name="ck_gstr1_txp_action",
        ),
        CheckConstraint(
            "filter_counterparty_gstin = '' OR LENGTH(filter_counterparty_gstin) = 15",
            name="ck_gstr1_txp_counterparty_len",
        ),
        Index("idx_gstr1_txp_period", "client_id", "year", "month"),
    )

    filter_counterparty_gstin: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
        default="",
        server_default=text("''"),
    )
    filter_action_required: Mapped[str] = mapped_column(
        String(1),
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


Gstr1AdvanceTaxRecord = Gstr1AdvanceTax
Gstr1B2BRecord = Gstr1B2B
Gstr1SummaryRecord = Gstr1Summary
Gstr1B2CSARecord = Gstr1B2CSA
Gstr1B2CSRecord = Gstr1B2CS
Gstr1CDNRRecord = Gstr1CDNR
Gstr1DocIssueRecord = Gstr1DocIssue
Gstr1HSNRecord = Gstr1HSN
Gstr1NilRecord = Gstr1Nil
Gstr1B2CLRecord = Gstr1B2CL
Gstr1CDNURRecord = Gstr1CDNUR
Gstr1EXPRecord = Gstr1EXP
Gstr1TXPRecord = Gstr1TXP


__all__ = [
    "Gstr1AdvanceTax",
    "Gstr1B2B",
    "Gstr1Summary",
    "Gstr1B2CSA",
    "Gstr1B2CS",
    "Gstr1CDNR",
    "Gstr1DocIssue",
    "Gstr1HSN",
    "Gstr1Nil",
    "Gstr1B2CL",
    "Gstr1CDNUR",
    "Gstr1EXP",
    "Gstr1TXP",
    "Gstr1AdvanceTaxRecord",
    "Gstr1B2BRecord",
    "Gstr1SummaryRecord",
    "Gstr1B2CSARecord",
    "Gstr1B2CSRecord",
    "Gstr1CDNRRecord",
    "Gstr1DocIssueRecord",
    "Gstr1HSNRecord",
    "Gstr1NilRecord",
    "Gstr1B2CLRecord",
    "Gstr1CDNURRecord",
    "Gstr1EXPRecord",
    "Gstr1TXPRecord",
]
