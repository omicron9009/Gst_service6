from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


Amount = Numeric(18, 2)
Rate = Numeric(7, 3)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class PrimaryKeyMixin:
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ClientScopeMixin:
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gstin: Mapped[str] = mapped_column(String(15), nullable=False, index=True)


class MonthlyPeriodMixin:
    year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True, index=True)
    month: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True, index=True)


class FinancialYearMixin:
    financial_year: Mapped[Optional[str]] = mapped_column(String(9), nullable=True, index=True)


class DateRangeMixin:
    from_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    to_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)


class RawPayloadMixin:
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class InvoiceFieldsMixin:
    invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    invoice_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)


class NoteFieldsMixin:
    note_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    note_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)


class TaxAmountsMixin:
    taxable_value: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    tax_rate: Mapped[Optional[Decimal]] = mapped_column(Rate, nullable=True)
    igst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    sgst: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)
    cess: Mapped[Optional[Decimal]] = mapped_column(Amount, nullable=True)


class JsonRecordMixin:
    record_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

