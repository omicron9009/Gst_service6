from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

import database
from database import Client


EXCLUDED_TABLES = {"clients", "client_sessions", "otp_requests"}
BUSINESS_TABLES = [
    "gstr1_advance_tax",
    "gstr1_b2b",
    "gstr1_summary",
    "gstr1_b2csa",
    "gstr1_b2cs",
    "gstr1_cdnr",
    "gstr1_doc_issue",
    "gstr1_hsn",
    "gstr1_nil",
    "gstr1_b2cl",
    "gstr1_cdnur",
    "gstr1_exp",
    "gstr1_txp",
    "gstr2a_b2b",
    "gstr2a_b2ba",
    "gstr2a_cdn",
    "gstr2a_cdna",
    "gstr2a_document",
    "gstr2a_isd",
    "gstr2a_tds",
    "gstr2b",
    "gstr2b_regen_status",
    "gstr3b_details",
    "gstr3b_auto_liability",
    "gstr9_auto_calculated",
    "gstr9_table8a",
    "gstr9_details",
    "ledger_balance",
    "ledger_cash",
    "ledger_itc",
    "ledger_liability",
    "gst_return_status",
]


def normalize_gstins(gstins: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for gstin in gstins or []:
        clean = (gstin or "").strip().upper()
        if not clean:
            continue
        if len(clean) != 15:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid GSTIN '{gstin}'. Expected exactly 15 characters.",
            )
        normalized.append(clean)
    return normalized


def resolve_requested_tables(tables: list[str] | None) -> list[str]:
    if not tables:
        return BUSINESS_TABLES.copy()

    requested = []
    unknown = []
    for table_name in tables:
        normalized = (table_name or "").strip()
        if not normalized:
            continue
        if normalized in EXCLUDED_TABLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Table '{normalized}' is excluded from proxy fetch.",
            )
        if normalized not in BUSINESS_TABLES:
            unknown.append(normalized)
            continue
        if normalized not in requested:
            requested.append(normalized)

    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Unknown table names requested.",
                "unknown_tables": unknown,
                "allowed_tables": BUSINESS_TABLES,
            },
        )

    if not requested:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid business tables requested.",
        )

    return requested


def make_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [make_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [make_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


async def fetch_clients(
    session: AsyncSession,
    *,
    gstins: list[str] | None,
    client_ids: list[int] | None,
    include_inactive: bool,
) -> list[dict[str, Any]]:
    stmt = select(
        Client.id,
        Client.gstin,
        Client.username,
        Client.trade_name,
        Client.legal_name,
        Client.is_active,
    )

    if not include_inactive:
        stmt = stmt.where(Client.is_active.is_(True))
    if gstins:
        stmt = stmt.where(Client.gstin.in_(gstins))
    if client_ids:
        stmt = stmt.where(Client.id.in_(client_ids))

    stmt = stmt.order_by(Client.gstin.asc())
    result = await session.execute(stmt)
    rows = result.mappings().all()
    return [make_json_safe(dict(row)) for row in rows]


async def fetch_table_rows(
    session: AsyncSession,
    *,
    table_name: str,
    client_ids: list[int],
) -> list[dict[str, Any]]:
    table = database.Base.metadata.tables[table_name]
    stmt: Select[Any] = (
        select(table)
        .where(table.c.client_id.in_(client_ids))
        .order_by(table.c.client_id.asc(), table.c.id.asc())
    )
    result = await session.execute(stmt)
    return [make_json_safe(dict(row)) for row in result.mappings().all()]


async def fetch_business_dataset(
    session: AsyncSession,
    *,
    gstins: list[str] | None,
    client_ids: list[int] | None,
    include_inactive: bool,
    tables: list[str] | None,
) -> dict[str, Any]:
    normalized_gstins = normalize_gstins(gstins)
    selected_tables = resolve_requested_tables(tables)
    clients = await fetch_clients(
        session,
        gstins=normalized_gstins,
        client_ids=client_ids,
        include_inactive=include_inactive,
    )

    if not clients:
        return {
            "filters": {
                "gstins": normalized_gstins,
                "client_ids": client_ids or [],
                "include_inactive": include_inactive,
                "tables": selected_tables,
            },
            "excluded_tables": sorted(EXCLUDED_TABLES),
            "summary": {
                "client_count": 0,
                "table_count": len(selected_tables),
                "total_rows": 0,
            },
            "table_row_counts": {table_name: 0 for table_name in selected_tables},
            "clients": [],
        }

    client_id_list = [int(client["id"]) for client in clients]
    clients_by_id: dict[int, dict[str, Any]] = {}
    for client in clients:
        client_id = int(client["id"])
        clients_by_id[client_id] = {
            "client_id": client_id,
            "gstin": client["gstin"],
            "trade_name": client.get("trade_name"),
            "legal_name": client.get("legal_name"),
            "is_active": client["is_active"],
            "tables": {
                table_name: {"row_count": 0, "rows": []} for table_name in selected_tables
            },
        }

    table_row_counts: dict[str, int] = {}
    total_rows = 0

    for table_name in selected_tables:
        rows = await fetch_table_rows(session, table_name=table_name, client_ids=client_id_list)
        grouped_rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped_rows[int(row["client_id"])].append(row)

        table_row_counts[table_name] = len(rows)
        total_rows += len(rows)

        for client_id in client_id_list:
            client_rows = grouped_rows.get(client_id, [])
            clients_by_id[client_id]["tables"][table_name] = {
                "row_count": len(client_rows),
                "rows": client_rows,
            }

    return {
        "filters": {
            "gstins": normalized_gstins,
            "client_ids": client_ids or [],
            "include_inactive": include_inactive,
            "tables": selected_tables,
        },
        "excluded_tables": sorted(EXCLUDED_TABLES),
        "summary": {
            "client_count": len(clients_by_id),
            "table_count": len(selected_tables),
            "total_rows": total_rows,
        },
        "table_row_counts": table_row_counts,
        "clients": list(clients_by_id.values()),
    }
