from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ...core.base import (
    Base,
    BigIntPrimaryKeyMixin,
    ClientForeignKeyMixin,
    FetchedUpdatedMixin,
    MonthlyPeriodMixin,
    StatusCodeMixin,
    UpstreamStatusCodeMixin,
    jsonb_object_default,
)


class _Gstr3BBase(
    BigIntPrimaryKeyMixin,
    ClientForeignKeyMixin,
    MonthlyPeriodMixin,
    StatusCodeMixin,
    UpstreamStatusCodeMixin,
    FetchedUpdatedMixin,
    Base,
):
    __abstract__ = True


class Gstr3BDetails(_Gstr3BBase):
    __tablename__ = "gstr3b_details"
    __table_args__ = (
        UniqueConstraint("client_id", "year", "month", name="uq_gstr3b_details"),
        Index("idx_gstr3b_details_period", "client_id", "year", "month"),
    )

    return_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    supply_details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=jsonb_object_default(),
    )
    inter_state_supplies: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=jsonb_object_default(),
    )
    eligible_itc: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=jsonb_object_default(),
    )
    inward_supplies: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=jsonb_object_default(),
    )
    interest_and_late_fee: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=jsonb_object_default(),
    )
    tax_payment: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=jsonb_object_default(),
    )


class Gstr3BAutoLiability(_Gstr3BBase):
    __tablename__ = "gstr3b_auto_liability"
    __table_args__ = (
        UniqueConstraint("client_id", "year", "month", name="uq_gstr3b_auto_liability"),
        Index("idx_gstr3b_auto_period", "client_id", "year", "month"),
    )

    auto_calculated_liability: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=jsonb_object_default(),
    )


Gstr3BDetailsRecord = Gstr3BDetails
Gstr3BAutoLiabilityRecord = Gstr3BAutoLiability


__all__ = [
    "Gstr3BDetails",
    "Gstr3BAutoLiability",
    "Gstr3BDetailsRecord",
    "Gstr3BAutoLiabilityRecord",
]
