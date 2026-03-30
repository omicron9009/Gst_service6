from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Index, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ...core.base import (
    Base,
    BigIntPrimaryKeyMixin,
    ClientForeignKeyMixin,
    DateRangeStringMixin,
    FetchedUpdatedMixin,
    MonthlyPeriodMixin,
    StatusCodeMixin,
    UpstreamStatusCodeMixin,
    jsonb_array_default,
)


class _LedgerBase(
    BigIntPrimaryKeyMixin,
    ClientForeignKeyMixin,
    StatusCodeMixin,
    UpstreamStatusCodeMixin,
    FetchedUpdatedMixin,
    Base,
):
    __abstract__ = True


class LedgerBalance(_LedgerBase, MonthlyPeriodMixin):
    __tablename__ = "ledger_balance"
    __table_args__ = (
        UniqueConstraint("client_id", "year", "month", name="uq_ledger_balance"),
        Index("idx_ledger_balance_period", "client_id", "year", "month"),
    )

    cash_igst_tax: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    cash_igst_interest: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    cash_igst_penalty: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    cash_igst_fee: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    cash_igst_other: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    cash_igst_total: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    cash_cgst_total: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    cash_sgst_total: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    cash_cess_total: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    itc_igst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    itc_cgst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    itc_sgst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    itc_cess: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    itc_blocked_igst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    itc_blocked_cgst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    itc_blocked_sgst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    itc_blocked_cess: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)


class LedgerCash(_LedgerBase, DateRangeStringMixin):
    __tablename__ = "ledger_cash"
    __table_args__ = (
        UniqueConstraint("client_id", "from_date", "to_date", name="uq_ledger_cash"),
        Index("idx_ledger_cash_dates", "client_id", "from_date", "to_date"),
    )

    opening_balance: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    closing_balance: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    transactions: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class LedgerItc(_LedgerBase, DateRangeStringMixin):
    __tablename__ = "ledger_itc"
    __table_args__ = (
        UniqueConstraint("client_id", "from_date", "to_date", name="uq_ledger_itc"),
        Index("idx_ledger_itc_dates", "client_id", "from_date", "to_date"),
    )

    opening_igst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    opening_cgst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    opening_sgst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    opening_cess: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    opening_total_range_balance: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    closing_igst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    closing_cgst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    closing_sgst: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    closing_cess: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    closing_total_range_balance: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    transactions: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )
    provisional_credit_balances: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)


class LedgerLiability(_LedgerBase, MonthlyPeriodMixin, DateRangeStringMixin):
    __tablename__ = "ledger_liability"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "year",
            "month",
            "from_date",
            "to_date",
            name="uq_ledger_liability",
        ),
        Index("idx_ledger_liability_period", "client_id", "year", "month"),
    )

    closing_balance: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    transactions: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


LedgerCashItcBalanceRecord = LedgerBalance
LedgerCashLedgerRecord = LedgerCash
LedgerItcLedgerRecord = LedgerItc
LedgerReturnLiabilityLedgerRecord = LedgerLiability


__all__ = [
    "LedgerBalance",
    "LedgerCash",
    "LedgerItc",
    "LedgerLiability",
    "LedgerCashItcBalanceRecord",
    "LedgerCashLedgerRecord",
    "LedgerItcLedgerRecord",
    "LedgerReturnLiabilityLedgerRecord",
]
