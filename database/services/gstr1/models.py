from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
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
    TaxAmountsMixin,
    TimestampMixin,
)


class _Gstr1Base(PrimaryKeyMixin, ClientScopeMixin, MonthlyPeriodMixin, RawPayloadMixin, TimestampMixin, Base):
    __abstract__ = True


class Gstr1AdvanceTaxRecord(_Gstr1Base):
    __tablename__ = "gstr1_advance_tax_records"

    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    supply_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    advance_amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    tax_rate: Mapped[Optional[Decimal]] = mapped_column(Rate, nullable=True)
    cgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    sgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cess: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    #igst 


class Gstr1B2BRecord(TaxAmountsMixin, _Gstr1Base):
    __tablename__ = "gstr1_b2b_records"

    counterparty_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    invoice_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    reverse_charge: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    invoice_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)


class Gstr1SummaryRecord(JsonRecordMixin, _Gstr1Base):
    __tablename__ = "gstr1_summary_records"

    section_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    counterparties: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    sub_sections: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
 # TaxAmountsMixin - cgst , igst , sgst , cess 


class Gstr1B2CSARecord(TaxAmountsMixin, _Gstr1Base):
    __tablename__ = "gstr1_b2csa_records"

    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    supply_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    invoice_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)


class Gstr1B2CSRecord(TaxAmountsMixin, _Gstr1Base):
    __tablename__ = "gstr1_b2cs_records"

    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    supply_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    invoice_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    flag: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)


class Gstr1CDNRRecord(TaxAmountsMixin, _Gstr1Base):
    __tablename__ = "gstr1_cdnr_records"

    counterparty_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    counter_filing_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    note_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    note_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    note_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    invoice_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    reverse_charge: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    note_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    flag: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    delete_flag: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    item_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Gstr1DocIssueRecord(_Gstr1Base):
    __tablename__ = "gstr1_doc_issue_records"

    document_type_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    from_serial: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_serial: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    total_issued: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cancelled: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    net_issued: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Gstr1HSNRecord(TaxAmountsMixin, _Gstr1Base):
    __tablename__ = "gstr1_hsn_records"

    serial_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hsn_sac_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    unit_of_quantity: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    quantity: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
# sep - b2b and  b2c values for (sn_sac_code , description , unit_of_quantity , quantity)

class Gstr1NilRecord(_Gstr1Base):
    __tablename__ = "gstr1_nil_records"

    supply_type_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    supply_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    nil_rated_amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    exempted_amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    non_gst_amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)


class Gstr1B2CLRecord(TaxAmountsMixin, _Gstr1Base):
    __tablename__ = "gstr1_b2cl_records"

    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    invoice_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    flag: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    item_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Gstr1CDNURRecord(TaxAmountsMixin, _Gstr1Base):
    __tablename__ = "gstr1_cdnur_records"

    note_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    note_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    note_type_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    note_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    supply_type_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    supply_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    note_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    flag: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    delete_flag: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    item_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Gstr1EXPRecord(TaxAmountsMixin, _Gstr1Base):
    __tablename__ = "gstr1_exp_records"

    export_type_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    export_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    invoice_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    flag: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    item_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Gstr1TXPRecord(_Gstr1Base):
    __tablename__ = "gstr1_txp_records"

    place_of_supply: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    supply_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    flag: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    action_required: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    item_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    advance_amount: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    tax_rate: Mapped[Optional[Decimal]] = mapped_column(Rate, nullable=True)
    igst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    sgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cess: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)


__all__ = [
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

