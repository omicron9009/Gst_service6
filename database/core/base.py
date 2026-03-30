from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CHAR, DateTime, ForeignKey, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


Amount = Numeric(15, 2)
LargeAmount = Numeric(18, 2)
Rate = Numeric(7, 3)


def jsonb_array_default():
    return text("'[]'::jsonb")


def jsonb_object_default():
    return text("'{}'::jsonb")


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class BigIntPrimaryKeyMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)


class ClientForeignKeyMixin:
    client_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
    )


class MonthlyPeriodMixin:
    year: Mapped[str] = mapped_column(String(4), nullable=False)
    month: Mapped[str] = mapped_column(String(2), nullable=False)


class FinancialYearMixin:
    financial_year: Mapped[str] = mapped_column(String(7), nullable=False)


class DateRangeStringMixin:
    from_date: Mapped[str] = mapped_column(String(10), nullable=False)
    to_date: Mapped[str] = mapped_column(String(10), nullable=False)


class CreatedUpdatedMixin:
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


class FetchedUpdatedMixin:
    fetched_at: Mapped[datetime] = mapped_column(
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


class UpstreamStatusCodeMixin:
    upstream_status_code: Mapped[int | None] = mapped_column(nullable=True)


class StatusCodeMixin:
    status_cd: Mapped[str | None] = mapped_column(String(10), nullable=True)


class GstinMixin:
    gstin: Mapped[str] = mapped_column(CHAR(15), nullable=False)


class UsernameMixin:
    username: Mapped[str] = mapped_column(String(100), nullable=False)


class JsonArrayMixin:
    records: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=jsonb_array_default(),
    )


class JsonObjectMixin:
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=jsonb_object_default(),
    )

