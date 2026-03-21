from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ...core.base import (
    Amount,
    Base,
    ClientScopeMixin,
    JsonRecordMixin,
    MonthlyPeriodMixin,
    PrimaryKeyMixin,
    RawPayloadMixin,
    TimestampMixin,
)


class _Gstr3BBase(PrimaryKeyMixin, ClientScopeMixin, MonthlyPeriodMixin, RawPayloadMixin, TimestampMixin, Base):
    __abstract__ = True


class Gstr3BDetailsRecord(JsonRecordMixin, _Gstr3BBase):
    __tablename__ = "gstr3b_details_records"

    section: Mapped[str] = mapped_column(String(50), nullable=False)
    subsection: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    line_code: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    line_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    transaction_type: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transaction_description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    liability_ledger_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    taxable_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    igst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    sgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cess: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)

    tax: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    interest: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    fee: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    penalty: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    other: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)

    inter_state_amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    intra_state_amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    event_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class Gstr3BAutoLiabilityRecord(JsonRecordMixin, _Gstr3BBase):
    __tablename__ = "gstr3b_auto_liability_records"

    section: Mapped[str] = mapped_column(String(50), nullable=False)
    subsection: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    source_table: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    taxable_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    igst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    sgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cess: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)


__all__ = ["Gstr3BDetailsRecord", "Gstr3BAutoLiabilityRecord"]
