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
    MonthlyPeriodMixin,
    PrimaryKeyMixin,
    Rate,
    RawPayloadMixin,
    TaxAmountsMixin,
    TimestampMixin,
)


class _Gstr2ABase(PrimaryKeyMixin, ClientScopeMixin, MonthlyPeriodMixin, RawPayloadMixin, TimestampMixin, Base):
    __abstract__ = True


class Gstr2AB2BRecord(TaxAmountsMixin, _Gstr2ABase):
    __tablename__ = "gstr2a_b2b_records"

    supplier_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    filing_status_gstr1: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    filing_status_gstr3b: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    supplier_filed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    supplier_filing_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    invoice_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    invoice_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    reverse_charge: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    irn: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    irn_gen_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    item_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Gstr2AB2BARecord(TaxAmountsMixin, _Gstr2ABase):
    __tablename__ = "gstr2a_b2ba_records"

    supplier_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    filing_status_gstr1: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    filing_status_gstr3b: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    supplier_filed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    supplier_filing_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    original_invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    original_invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    amendment_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    amendment_type_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    amendment_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    invoice_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    invoice_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    reverse_charge: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    item_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Gstr2ACDNRecord(TaxAmountsMixin, _Gstr2ABase):
    __tablename__ = "gstr2a_cdn_records"

    supplier_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    filing_status_gstr1: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    filing_status_gstr3b: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    supplier_filed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    supplier_filing_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    note_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    note_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    note_type_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    note_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    invoice_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    note_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    reverse_charge: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    delete_flag: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    irn: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    irn_gen_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    item_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Gstr2ACDNARecord(TaxAmountsMixin, _Gstr2ABase):
    __tablename__ = "gstr2a_cdna_records"

    supplier_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    filing_status_gstr1: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    note_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    note_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    original_note_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    original_note_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    note_type_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    note_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    invoice_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    note_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    reverse_charge: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    delete_flag: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    diff_percent: Mapped[Optional[Decimal]] = mapped_column(Rate, nullable=True)
    pre_gst: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    item_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Gstr2ADocumentRecord(TaxAmountsMixin, _Gstr2ABase):
    __tablename__ = "gstr2a_document_records"

    section: Mapped[str] = mapped_column(String(20), nullable=False)
    supplier_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    filing_status_gstr1: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    filing_status_gstr3b: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    supplier_filed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    supplier_filing_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    original_invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    original_invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    amendment_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    amendment_type_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    amendment_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    note_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    note_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    note_type_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    note_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    invoice_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    invoice_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    note_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    reverse_charge: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    delete_flag: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    irn: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    irn_gen_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    item_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Gstr2AISDRecord(_Gstr2ABase):
    __tablename__ = "gstr2a_isd_records"

    distributor_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    filing_status_gstr1: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    document_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    document_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    document_type_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    document_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    itc_eligible: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    igst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    sgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cess: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)


class Gstr2ATDSRecord(_Gstr2ABase):
    __tablename__ = "gstr2a_tds_records"

    deductor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    deductor_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    recipient_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    return_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    deduction_base_amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    igst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    sgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)


__all__ = [
    "Gstr2AB2BRecord",
    "Gstr2AB2BARecord",
    "Gstr2ACDNRecord",
    "Gstr2ACDNARecord",
    "Gstr2ADocumentRecord",
    "Gstr2AISDRecord",
    "Gstr2ATDSRecord",
]

