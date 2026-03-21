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
    Rate,
    RawPayloadMixin,
    TimestampMixin,
)


class _Gstr2BBase(PrimaryKeyMixin, ClientScopeMixin, MonthlyPeriodMixin, RawPayloadMixin, TimestampMixin, Base):
    __abstract__ = True


class Gstr2BRecord(JsonRecordMixin, _Gstr2BBase):
    __tablename__ = "gstr2b_records"

    status_cd: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    response_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    file_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    supplier_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    supplier_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    supplier_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    supplier_file_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    original_invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    original_invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    note_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    note_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    original_note_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    original_note_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    note_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    supply_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    document_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    document_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    document_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    invoice_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    reverse_charge: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    itc_available: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    diff_percent: Mapped[Optional[Decimal]] = mapped_column(Rate, nullable=True)

    taxable_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    tax_rate: Mapped[Optional[Decimal]] = mapped_column(Rate, nullable=True)
    invoice_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    note_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    igst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    sgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cess: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)

    source_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ims_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    irn: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    irn_gen_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    item_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Gstr2BRegenerationStatusRecord(_Gstr2BBase):
    __tablename__ = "gstr2b_regeneration_status_records"

    reference_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    regeneration_status: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    regeneration_status_label: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


__all__ = ["Gstr2BRecord", "Gstr2BRegenerationStatusRecord"]

