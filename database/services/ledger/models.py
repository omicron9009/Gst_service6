from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from ...core.base import (
    Amount,
    Base,
    ClientScopeMixin,
    DateRangeMixin,
    JsonRecordMixin,
    MonthlyPeriodMixin,
    PrimaryKeyMixin,
    RawPayloadMixin,
    TimestampMixin,
)


class _LedgerBase(PrimaryKeyMixin, ClientScopeMixin, RawPayloadMixin, TimestampMixin, Base):
    __abstract__ = True


class LedgerCashItcBalanceRecord(MonthlyPeriodMixin, _LedgerBase):
    __tablename__ = "ledger_cash_itc_balance_records"

    snapshot_type: Mapped[str] = mapped_column(String(40), nullable=False)
    tax_head: Mapped[str] = mapped_column(String(10), nullable=False)
    component: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)


class LedgerCashLedgerRecord(DateRangeMixin, JsonRecordMixin, _LedgerBase):
    __tablename__ = "ledger_cash_ledger_records"

    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    transaction_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    transaction_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    discharge_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tax_head: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    component: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    balance_amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    total_transaction_amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    total_range_balance: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)


class LedgerItcLedgerRecord(DateRangeMixin, JsonRecordMixin, _LedgerBase):
    __tablename__ = "ledger_itc_ledger_records"

    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    transaction_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    return_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    transaction_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    tax_head: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    balance_after: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    total_transaction_amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    total_range_balance: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)


class LedgerReturnLiabilityLedgerRecord(MonthlyPeriodMixin, DateRangeMixin, JsonRecordMixin, _LedgerBase):
    __tablename__ = "ledger_return_liability_ledger_records"

    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    transaction_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    transaction_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    discharge_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tax_head: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    component: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    balance_after: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    total_transaction_amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    total_range_balance_after: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)


__all__ = [
    "LedgerCashItcBalanceRecord",
    "LedgerCashLedgerRecord",
    "LedgerItcLedgerRecord",
    "LedgerReturnLiabilityLedgerRecord",
]

