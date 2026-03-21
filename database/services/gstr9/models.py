from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ...core.base import (
    Amount,
    Base,
    ClientScopeMixin,
    FinancialYearMixin,
    JsonRecordMixin,
    PrimaryKeyMixin,
    Rate,
    RawPayloadMixin,
    TimestampMixin,
)


class _Gstr9Base(PrimaryKeyMixin, ClientScopeMixin, FinancialYearMixin, RawPayloadMixin, TimestampMixin, Base):
    __abstract__ = True


class _Gstr9LineMixin:
    table_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    section_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    section_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    supplier_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    filing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    return_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    original_invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    original_invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    note_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    note_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    note_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    invoice_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    reverse_charge: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    hsn_sac: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_concessional: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    tax_rate: Mapped[Optional[Decimal]] = mapped_column(Rate, nullable=True)
    taxable_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    invoice_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    igst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    sgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cess: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)

    amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    tax_payable: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    paid_in_cash: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    paid_via_igst_itc: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    paid_via_cgst_itc: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    paid_via_sgst_itc: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    paid_via_cess_itc: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)


class Gstr9AutoCalculatedRecord(_Gstr9LineMixin, JsonRecordMixin, _Gstr9Base):
    __tablename__ = "gstr9_auto_calculated_records"


class Gstr9Table8ARecord(_Gstr9LineMixin, _Gstr9Base):
    __tablename__ = "gstr9_table8a_records"

    file_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_eligible: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    ineligibility_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Gstr9DetailsRecord(_Gstr9LineMixin, JsonRecordMixin, _Gstr9Base):
    __tablename__ = "gstr9_details_records"


__all__ = [
    "Gstr9AutoCalculatedRecord",
    "Gstr9Table8ARecord",
    "Gstr9DetailsRecord",
]

