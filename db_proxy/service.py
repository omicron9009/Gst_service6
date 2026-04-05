from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal
from html import escape
from typing import Any, Iterable

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

REPORT_TABLES = [table for table in BUSINESS_TABLES if not table.startswith("gstr9_")]

NESTED_ARRAY_KEYS: dict[str, str] = {
    "gstr1_b2b": "invoices",
    "gstr1_b2csa": "records",
    "gstr1_b2cs": "records",
    "gstr1_cdnr": "records",
    "gstr1_cdnur": "records",
    "gstr1_exp": "records",
    "gstr1_nil": "records",
    "gstr1_hsn": "records",
    "gstr1_doc_issue": "records",
    "gstr1_b2cl": "records",
    "gstr1_txp": "records",
    "gstr1_advance_tax": "records",
    "gstr1_summary": "sections",
    "gstr2a_b2b": "records",
    "gstr2a_b2ba": "records",
    "gstr2a_cdn": "records",
    "gstr2a_cdna": "records",
    "gstr2a_document": "records",
    "gstr2a_isd": "records",
    "gstr2a_tds": "records",
    "gstr2b": "records",
    "gstr3b_details": "records",
    "gstr3b_auto_liability": "records",
    "ledger_balance": "records",
    "ledger_cash": "transactions",
    "ledger_itc": "transactions",
    "ledger_liability": "transactions",
}

ALLOWED_NUMERIC_KEYS = {
    "taxable_value", "invoice_value", "note_value", "total_taxable_value",
    "total_cgst", "total_sgst", "total_igst", "cgst", "sgst", "igst", "cess",
    "rate", "total_invoices", "ttl_rec", "ttl_val", "ttl_tax", "ttl_igst",
    "ttl_cgst", "ttl_sgst", "ttl_cess", "cash_igst_tax", "cash_igst_interest",
    "cash_igst_penalty", "cash_igst_fee", "cash_igst_other", "cash_igst_total",
    "cash_cgst_total", "cash_sgst_total", "cash_cess_total", "itc_igst",
    "itc_cgst", "itc_sgst", "itc_cess", "itc_blocked_igst", "itc_blocked_cgst",
    "itc_blocked_sgst", "itc_blocked_cess", "igst_amt", "cgst_amt", "sgst_amt",
    "cess_amt", "total_amount", "igst_bal", "cgst_bal", "sgst_bal", "cess_bal",
    "total_range_balance", "tot_tr_amt", "tot_rng_bal", "opening_igst",
    "opening_cgst", "opening_sgst", "opening_cess", "opening_total_range_balance",
    "closing_igst", "closing_cgst", "closing_sgst", "closing_cess",
    "closing_total_range_balance",
}

EXCLUDED_TABLE_COLUMNS = {
    "id", "client_id", "status_code", "upstream_status_code", "fetched_at",
    "created_at", "updated_at", "year", "month", "ret_period",
    "filter_action_required", "filter_from_date", "filter_counterparty_gstin",
    "record_count", "total_invoices", "summary_type",
}

TABLE_LABELS: dict[str, str] = {
    "gstr1_summary": "GSTR-1 Summary",
    "gstr1_b2b": "B2B — Business to Business",
    "gstr1_b2cs": "B2CS — Small Consumer Invoices",
    "gstr1_b2csa": "B2CSA — Amended Small Consumer",
    "gstr1_b2cl": "B2CL — Large Consumer Invoices",
    "gstr1_cdnr": "CDNR — Credit/Debit Notes (Registered)",
    "gstr1_cdnur": "CDNUR — Credit/Debit Notes (Unregistered)",
    "gstr1_exp": "EXP — Export Invoices",
    "gstr1_nil": "NIL — Nil Rated / Exempt / Non-GST Supplies",
    "gstr1_hsn": "HSN — HSN-wise Summary",
    "gstr1_doc_issue": "Document Issuance Summary",
    "gstr1_advance_tax": "AT — Advance Tax Received",
    "gstr1_txp": "TXP — Advance Adjusted",
    "gstr2a_b2b": "B2B — Auto-Drafted Inward Supplies",
    "gstr2a_b2ba": "B2BA — Amended Auto-Drafted B2B",
    "gstr2a_cdn": "CDN — Credit/Debit Notes",
    "gstr2a_cdna": "CDNA — Amended Credit/Debit Notes",
    "gstr2a_document": "Document Summary",
    "gstr2a_isd": "ISD — Input Service Distributor",
    "gstr2a_tds": "TDS — Tax Deducted at Source",
    "gstr2b": "GSTR-2B Invoice Statement",
    "gstr2b_regen_status": "GSTR-2B Regeneration Status",
    "gstr3b_details": "GSTR-3B Return Details",
    "gstr3b_auto_liability": "GSTR-3B Auto-Computed Liability",
    "ledger_balance": "Balance Summary",
    "ledger_cash": "Cash Ledger — Transactions",
    "ledger_itc": "ITC Ledger — Transactions",
    "ledger_liability": "Return Liability Ledger",
    "gst_return_status": "GST Return Filing Status",
}

TABLE_CHAPTERS: dict[str, list[str]] = {
    "GSTR-1 — Outward Supplies": [
        "gstr1_summary", "gstr1_b2b", "gstr1_b2csa", "gstr1_b2cs",
        "gstr1_b2cl", "gstr1_cdnr", "gstr1_cdnur", "gstr1_exp",
        "gstr1_nil", "gstr1_hsn", "gstr1_doc_issue", "gstr1_advance_tax", "gstr1_txp",
    ],
    "GSTR-2A — Auto-Drafted Inward Supplies": [
        "gstr2a_b2b", "gstr2a_b2ba", "gstr2a_cdn", "gstr2a_cdna",
        "gstr2a_document", "gstr2a_isd", "gstr2a_tds",
    ],
    "GSTR-2B — ITC Statement": [
        "gstr2b", "gstr2b_regen_status",
    ],
    "GSTR-3B — Self-Assessment Return": [
        "gstr3b_details", "gstr3b_auto_liability",
    ],
    "Electronic Ledgers": [
        "ledger_balance", "ledger_cash", "ledger_itc", "ledger_liability",
    ],
    "GST Return Filing Status": [
        "gst_return_status",
    ],
}

CHAPTER_COLORS = [
    ("#1B4FD8", "#EEF2FF"),  # Blue  (GSTR-1)
    ("#6D28D9", "#F5F3FF"),  # Purple (GSTR-2A)
    ("#0D7490", "#ECFEFF"),  # Cyan  (GSTR-2B)
    ("#B45309", "#FFFBEB"),  # Amber (GSTR-3B)
    ("#15803D", "#F0FDF4"),  # Green (Ledgers)
    ("#B91C1C", "#FEF2F2"),  # Red   (Status)
]

CHART_PALETTE = ["#1B4FD8", "#6D28D9", "#0D7490", "#B45309", "#15803D", "#B91C1C", "#0F766E"]


# ─────────────────────────────────────────────
# CORE DATA UTILITIES
# ─────────────────────────────────────────────

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
    stmt = select(Client.id, Client.gstin, Client.username, Client.trade_name, Client.legal_name, Client.is_active)
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
    year: str | None = None,
    month: str | None = None,
) -> list[dict[str, Any]]:
    table = database.Base.metadata.tables[table_name]
    stmt: Select[Any] = select(table).where(table.c.client_id.in_(client_ids))
    if year is not None and "year" in table.c:
        stmt = stmt.where(table.c.year == year)
    if month is not None and "month" in table.c:
        stmt = stmt.where(table.c.month == month)
    stmt = stmt.order_by(table.c.client_id.asc(), table.c.id.asc())
    result = await session.execute(stmt)
    return [make_json_safe(dict(row)) for row in result.mappings().all()]


async def fetch_business_dataset(
    session: AsyncSession,
    *,
    gstins: list[str] | None,
    client_ids: list[int] | None,
    include_inactive: bool,
    tables: list[str] | None,
    year: str | None = None,
    month: str | None = None,
) -> dict[str, Any]:
    normalized_gstins = normalize_gstins(gstins)
    selected_tables = resolve_requested_tables(tables)
    clients = await fetch_clients(
        session, gstins=normalized_gstins, client_ids=client_ids,
        include_inactive=include_inactive,
    )
    if not clients:
        return {
            "filters": {"gstins": normalized_gstins, "client_ids": client_ids or [],
                        "include_inactive": include_inactive, "tables": selected_tables,
                        "year": year, "month": month},
            "excluded_tables": sorted(EXCLUDED_TABLES),
            "summary": {"client_count": 0, "table_count": len(selected_tables), "total_rows": 0},
            "table_row_counts": {t: 0 for t in selected_tables},
            "clients": [],
        }
    client_id_list = [int(c["id"]) for c in clients]
    clients_by_id: dict[int, dict[str, Any]] = {}
    for client in clients:
        cid = int(client["id"])
        clients_by_id[cid] = {
            "client_id": cid,
            "gstin": client["gstin"],
            "trade_name": client.get("trade_name"),
            "legal_name": client.get("legal_name"),
            "is_active": client["is_active"],
            "tables": {t: {"row_count": 0, "rows": []} for t in selected_tables},
        }
    table_row_counts: dict[str, int] = {}
    total_rows = 0
    for table_name in selected_tables:
        rows = await fetch_table_rows(session, table_name=table_name,
                                      client_ids=client_id_list, year=year, month=month)
        grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[int(row["client_id"])].append(row)
        table_row_counts[table_name] = len(rows)
        total_rows += len(rows)
        for cid in client_id_list:
            cr = grouped.get(cid, [])
            clients_by_id[cid]["tables"][table_name] = {"row_count": len(cr), "rows": cr}
    return {
        "filters": {"gstins": normalized_gstins, "client_ids": client_ids or [],
                    "include_inactive": include_inactive, "tables": selected_tables,
                    "year": year, "month": month},
        "excluded_tables": sorted(EXCLUDED_TABLES),
        "summary": {"client_count": len(clients_by_id), "table_count": len(selected_tables),
                    "total_rows": total_rows},
        "table_row_counts": table_row_counts,
        "clients": list(clients_by_id.values()),
    }


async def fetch_available_periods(
    session: AsyncSession,
    *,
    gstins: list[str] | None,
) -> dict[str, Any]:
    normalized_gstins = normalize_gstins(gstins)
    if not normalized_gstins:
        return {"periods": []}
    client_stmt = select(Client.id).where(Client.gstin.in_(normalized_gstins))
    client_result = await session.execute(client_stmt)
    client_ids = [row[0] for row in client_result.all()]
    if not client_ids:
        return {"periods": []}
    periods_set: set[tuple[str, str]] = set()
    monthly_tables = [
        "gstr1_advance_tax", "gstr1_b2b", "gstr1_summary", "gstr1_b2csa",
        "gstr1_b2cs", "gstr1_cdnr", "gstr1_doc_issue", "gstr1_hsn",
        "gstr1_nil", "gstr1_b2cl", "gstr1_cdnur", "gstr1_exp", "gstr1_txp",
        "gstr2a_b2b", "gstr2a_b2ba", "gstr2a_cdn", "gstr2a_cdna",
        "gstr2a_document", "gstr2a_isd", "gstr2a_tds",
        "gstr2b", "gstr2b_regen_status",
    ]
    for table_name in monthly_tables:
        if table_name not in database.Base.metadata.tables:
            continue
        table = database.Base.metadata.tables[table_name]
        if "year" not in table.c or "month" not in table.c:
            continue
        stmt = (
            select(table.c.year, table.c.month)
            .where(table.c.client_id.in_(client_ids))
            .distinct()
        )
        result = await session.execute(stmt)
        for row in result.all():
            year, month = row
            if year and month:
                periods_set.add((str(year), str(month)))
    periods = sorted(periods_set)
    return {"periods": [{"year": y, "month": m} for y, m in periods]}


# ─────────────────────────────────────────────
# AGGREGATION HELPERS
# ─────────────────────────────────────────────

def _resolve_numeric_key(key_hint: str | None) -> str | None:
    if not key_hint:
        return None
    if key_hint in ALLOWED_NUMERIC_KEYS:
        return key_hint
    for sep in (".", "_"):
        candidate = key_hint.split(sep)[-1]
        if candidate in ALLOWED_NUMERIC_KEYS:
            return candidate
    return None


def _accumulate_numeric(value: Any, totals: dict[str, Decimal], key_hint: str | None = None) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            _accumulate_numeric(v, totals, k)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _accumulate_numeric(item, totals, key_hint)
        return
    numeric_key = _resolve_numeric_key(key_hint)
    if numeric_key is None:
        return
    try:
        totals[numeric_key] += Decimal(str(value))
    except Exception:
        return


def _aggregate_numeric(records: Iterable[dict[str, Any]]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for record in records:
        _accumulate_numeric(record, totals)
    return totals


def _normalize_row(record: dict[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                flattened[f"{key}_{child_key}"] = child_value
        else:
            flattened[key] = value
    return make_json_safe(flattened)


def _flatten_table_rows(table_name: str, table_data: dict[str, Any]) -> list[dict[str, Any]]:
    nested_key = NESTED_ARRAY_KEYS.get(table_name)
    rows = table_data.get("rows", []) if isinstance(table_data, dict) else []
    flattened: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if nested_key and isinstance(row.get(nested_key), list):
            for item in row[nested_key]:
                if isinstance(item, dict):
                    flattened.append(_normalize_row(item))
        else:
            flattened.append(_normalize_row(row))
    return flattened


def _select_columns(rows: list[dict[str, Any]], *, max_columns: int = 10) -> list[str]:
    column_counts: Counter[str] = Counter()
    for row in rows:
        for key in row.keys():
            if key in EXCLUDED_TABLE_COLUMNS:
                continue
            column_counts[key] += 1
    return [col for col, _ in column_counts.most_common(max_columns)]


def _sum_table_fields(
    table_summaries: dict[str, dict[str, Any]],
    table_name: str,
    keys: list[str],
) -> Decimal:
    summary = table_summaries.get(table_name)
    if not summary:
        return Decimal("0")
    numeric_totals: dict[str, Decimal] = summary.get("numeric_totals", {})  # type: ignore[assignment]
    return sum((numeric_totals.get(k, Decimal("0")) for k in keys), Decimal("0"))


# ─────────────────────────────────────────────
# FORMATTING HELPERS
# ─────────────────────────────────────────────

def _fmt_num(value: Any) -> str:
    try:
        d = Decimal(str(value))
        if d == 0:
            return "—"
        return f"{d:,.2f}"
    except Exception:
        return escape(str(value))


def _fmt_currency(amount: Decimal) -> str:
    try:
        if amount == 0:
            return "₹ 0.00"
        return f"₹ {amount:,.2f}"
    except Exception:
        return "₹ 0.00"


def _fmt_currency_compact(amount: Decimal) -> str:
    try:
        abs_amt = abs(amount)
        if abs_amt >= Decimal("10000000"):
            return f"₹ {float(amount / 10000000):.2f} Cr"
        if abs_amt >= Decimal("100000"):
            return f"₹ {float(amount / 100000):.2f} L"
        return f"₹ {amount:,.2f}"
    except Exception:
        return "₹ 0.00"


_MONTH_NAMES = {
    "01": "January", "02": "February", "03": "March", "04": "April",
    "05": "May", "06": "June", "07": "July", "08": "August",
    "09": "September", "10": "October", "11": "November", "12": "December",
}


# ─────────────────────────────────────────────
# SVG CHART GENERATORS
# ─────────────────────────────────────────────

def _svg_horizontal_bars(
    data: list[tuple[str, Decimal]],
    title: str,
    color: str = "#1B4FD8",
    width: int = 500,
) -> str:
    data = [(label, val) for label, val in data if val > 0]
    if not data:
        return f'<p style="color:#94A3B8;font-size:12px;margin:8px 0;">No data available — {escape(title)}</p>'

    max_val = max(v for _, v in data) or Decimal("1")
    bar_h = 28
    gap = 9
    label_w = 150
    value_w = 110
    bar_area = width - label_w - value_w
    chart_h = len(data) * (bar_h + gap) + 44

    rows_svg = ""
    for i, (label, value) in enumerate(data):
        y = 36 + i * (bar_h + gap)
        bw = max(3, int(float(value / max_val) * bar_area))
        pct = float(value / max_val) * 100
        lighter = color + "55"
        rows_svg += f"""
        <text x="{label_w - 10}" y="{y + bar_h // 2 + 4}" text-anchor="end"
              font-size="10.5" fill="#5B6478" font-family="'IBM Plex Sans',sans-serif">{escape(label[:22])}</text>
        <rect x="{label_w}" y="{y}" width="{bar_area}" height="{bar_h}" rx="5" fill="#F1F5F9"/>
        <rect x="{label_w}" y="{y}" width="{bw}" height="{bar_h}" rx="5" fill="{color}" opacity="0.88"/>
        <text x="{label_w + bar_area + 8}" y="{y + bar_h // 2 + 4}"
              font-size="10" fill="#1E293B" font-weight="600"
              font-family="'IBM Plex Mono',monospace">{_fmt_currency(value)}</text>"""

    return f"""<svg width="{width}" height="{chart_h}" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <style>text {{ font-family: 'IBM Plex Sans', sans-serif; }}</style>
      </defs>
      <text x="0" y="17" font-size="14" font-weight="700" fill="#0D1321"
            font-family="'IBM Plex Sans',sans-serif">{escape(title)}</text>
      <line x1="{label_w}" y1="24" x2="{label_w}" y2="{chart_h - 4}"
            stroke="#E2E8F0" stroke-width="1.5"/>
      {rows_svg}
    </svg>"""


def _svg_donut(
    segments: list[tuple[str, Decimal, str]],
    title: str,
) -> str:
    segments = [(l, v, c) for l, v, c in segments if v > 0]
    if not segments:
        return f'<p style="color:#94A3B8;font-size:12px;margin:8px 0;">No data — {escape(title)}</p>'

    total = sum(v for _, v, _ in segments) or Decimal("1")
    cx, cy = 115, 130
    ro, ri = 90, 52
    svg_w = 460

    arcs = []
    legend_items = []
    angle = -math.pi / 2

    for i, (label, value, color) in enumerate(segments):
        frac = float(value / total)
        span = frac * 2 * math.pi
        end_a = angle + span
        x1, y1 = cx + ro * math.cos(angle), cy + ro * math.sin(angle)
        x2, y2 = cx + ro * math.cos(end_a), cy + ro * math.sin(end_a)
        ix1, iy1 = cx + ri * math.cos(end_a), cy + ri * math.sin(end_a)
        ix2, iy2 = cx + ri * math.cos(angle), cy + ri * math.sin(angle)
        lf = 1 if span > math.pi else 0
        d = (f"M{x1:.2f} {y1:.2f} A{ro} {ro} 0 {lf} 1 {x2:.2f} {y2:.2f} "
             f"L{ix1:.2f} {iy1:.2f} A{ri} {ri} 0 {lf} 0 {ix2:.2f} {iy2:.2f}Z")
        arcs.append(f'<path d="{d}" fill="{color}"/>')
        angle = end_a

        ly = 50 + i * 26
        pct_str = f"{frac * 100:.1f}%"
        legend_items.append(f"""
        <rect x="238" y="{ly}" width="11" height="11" rx="2.5" fill="{color}"/>
        <text x="256" y="{ly + 9.5}" font-size="10.5" fill="#374151"
              font-family="'IBM Plex Sans',sans-serif">{escape(label)}</text>
        <text x="{svg_w - 6}" y="{ly + 9.5}" font-size="10" fill="#0D1321" font-weight="600"
              text-anchor="end" font-family="'IBM Plex Mono',monospace">{_fmt_currency(value)}</text>
        <text x="{svg_w - 6}" y="{ly + 21}" font-size="9" fill="#94A3B8"
              text-anchor="end" font-family="'IBM Plex Sans',sans-serif">{pct_str}</text>""")

    total_str = _fmt_currency_compact(total)
    return f"""<svg width="{svg_w}" height="260" xmlns="http://www.w3.org/2000/svg">
      <text x="{svg_w // 2}" y="17" text-anchor="middle" font-size="14" font-weight="700" fill="#0D1321"
            font-family="'IBM Plex Sans',sans-serif">{escape(title)}</text>
      {''.join(arcs)}
      <circle cx="{cx}" cy="{cy}" r="{ri - 3}" fill="white"/>
      <text x="{cx}" y="{cy - 7}" text-anchor="middle" font-size="8.5" fill="#94A3B8"
            letter-spacing="0.8" font-family="'IBM Plex Sans',sans-serif">TOTAL</text>
      <text x="{cx}" y="{cy + 9}" text-anchor="middle" font-size="11" font-weight="700" fill="#0D1321"
            font-family="'IBM Plex Mono',monospace">{escape(total_str)}</text>
      {''.join(legend_items)}
    </svg>"""


def _svg_grouped_bars(
    groups: list[tuple[str, list[tuple[str, Decimal]]]],
    title: str,
    colors: list[str] | None = None,
    width: int = 540,
) -> str:
    if not groups:
        return ""
    if colors is None:
        colors = CHART_PALETTE

    all_series: list[str] = []
    for _, series in groups:
        for sl, _ in series:
            if sl not in all_series:
                all_series.append(sl)

    n_groups = len(groups)
    n_series = len(all_series)
    bar_w = 14
    group_w = n_series * bar_w + (n_series - 1) * 3 + 16
    left_margin = 50
    bottom_margin = 40
    top_margin = 36
    chart_h = 220

    plot_h = chart_h - top_margin - bottom_margin
    plot_w = width - left_margin - 10

    all_vals = [v for _, series in groups for _, v in series]
    max_val = max(all_vals) if all_vals else Decimal("1")
    if max_val == 0:
        max_val = Decimal("1")

    bars_svg = ""
    for gi, (group_label, series) in enumerate(groups):
        series_map = dict(series)
        gx = left_margin + gi * (plot_w // n_groups) + (plot_w // n_groups - group_w) // 2
        for si, sl in enumerate(all_series):
            val = series_map.get(sl, Decimal("0"))
            bh = int(float(val / max_val) * plot_h)
            bx = gx + si * (bar_w + 3)
            by = top_margin + plot_h - bh
            col = colors[si % len(colors)]
            bars_svg += f'<rect x="{bx}" y="{by}" width="{bar_w}" height="{bh}" rx="3" fill="{col}" opacity="0.85"/>'
        glx = left_margin + gi * (plot_w // n_groups) + (plot_w // n_groups) // 2
        bars_svg += f'<text x="{glx}" y="{chart_h - bottom_margin + 16}" text-anchor="middle" font-size="9.5" fill="#64748B" font-family="\'IBM Plex Sans\',sans-serif">{escape(group_label[:14])}</text>'

    ticks_svg = ""
    for ti in range(5):
        tv = max_val * Decimal(ti) / 4
        ty = top_margin + plot_h - int(float(tv / max_val) * plot_h)
        ticks_svg += f'<line x1="{left_margin - 4}" y1="{ty}" x2="{width - 10}" y2="{ty}" stroke="#F1F5F9" stroke-width="1"/>'
        ticks_svg += f'<text x="{left_margin - 6}" y="{ty + 4}" text-anchor="end" font-size="8.5" fill="#94A3B8" font-family="\'IBM Plex Mono\',monospace">{_fmt_currency_compact(tv)}</text>'

    legend_svg = ""
    lx = left_margin
    for si, sl in enumerate(all_series):
        col = colors[si % len(colors)]
        legend_svg += f'<rect x="{lx}" y="{chart_h - 12}" width="9" height="9" rx="2" fill="{col}"/>'
        legend_svg += f'<text x="{lx + 12}" y="{chart_h - 4}" font-size="9" fill="#64748B" font-family="\'IBM Plex Sans\',sans-serif">{escape(sl)}</text>'
        lx += len(sl) * 6 + 22

    return f"""<svg width="{width}" height="{chart_h}" xmlns="http://www.w3.org/2000/svg">
      <text x="0" y="17" font-size="14" font-weight="700" fill="#0D1321"
            font-family="'IBM Plex Sans',sans-serif">{escape(title)}</text>
      <line x1="{left_margin}" y1="{top_margin}" x2="{left_margin}" y2="{chart_h - bottom_margin}"
            stroke="#CBD5E1" stroke-width="1.5"/>
      <line x1="{left_margin}" y1="{chart_h - bottom_margin}" x2="{width - 10}" y2="{chart_h - bottom_margin}"
            stroke="#CBD5E1" stroke-width="1.5"/>
      {ticks_svg}
      {bars_svg}
      {legend_svg}
    </svg>"""


# ─────────────────────────────────────────────
# HTML TABLE RENDERING
# ─────────────────────────────────────────────

def _is_numeric_col(col: str) -> bool:
    return _resolve_numeric_key(col) is not None or any(
        col.endswith(s) for s in ("_amt", "_bal", "_value", "_total", "_igst", "_cgst", "_sgst", "_cess")
    )


def _render_table(
    title: str,
    rows: list[dict[str, Any]],
    accent_color: str = "#1B4FD8",
    accent_bg: str = "#EEF2FF",
    *,
    max_rows: int = 100,
) -> str:
    safe_title = escape(title)
    row_count = len(rows)

    if not rows:
        return f"""
        <div class="tbl-wrap" style="--accent:{accent_color};--accent-bg:{accent_bg};">
          <div class="tbl-header">
            <span class="tbl-title">{safe_title}</span>
            <span class="tbl-badge">0 records</span>
          </div>
          <div class="tbl-empty">No records available for this period.</div>
        </div>"""

    display_rows = rows[:max_rows]
    columns = _select_columns(display_rows, max_columns=12)

    if not columns:
        return f"""
        <div class="tbl-wrap" style="--accent:{accent_color};--accent-bg:{accent_bg};">
          <div class="tbl-header">
            <span class="tbl-title">{safe_title}</span>
            <span class="tbl-badge">{row_count} records</span>
          </div>
          <div class="tbl-empty">No displayable columns.</div>
        </div>"""

    numeric_cols = [c for c in columns if _is_numeric_col(c)]
    col_totals: dict[str, Decimal] = defaultdict(Decimal)
    for row in display_rows:
        for nc in numeric_cols:
            try:
                col_totals[nc] += Decimal(str(row.get(nc, 0) or 0))
            except Exception:
                pass

    header_cells = "".join(
        f'<th class="{"num-col" if _is_numeric_col(c) else ""}">{escape(c.replace("_", " ").title())}</th>'
        for c in columns
    )

    body_rows = ""
    for row in display_rows:
        cells = ""
        for col in columns:
            val = row.get(col, "")
            if _is_numeric_col(col):
                cells += f'<td class="num-col">{_fmt_num(val)}</td>'
            else:
                display = escape(str(val)) if val not in ("", None) else '<span style="color:#CBD5E1">—</span>'
                cells += f"<td>{display}</td>"
        body_rows += f"<tr>{cells}</tr>"

    footer_row = ""
    if numeric_cols:
        foot_cells = ""
        for col in columns:
            if col in col_totals and col_totals[col] != 0:
                foot_cells += f'<td class="num-col tbl-total">{_fmt_num(col_totals[col])}</td>'
            elif col == columns[0]:
                foot_cells += '<td class="tbl-total" style="color:#64748B;font-style:italic;">Totals</td>'
            else:
                foot_cells += '<td class="tbl-total"></td>'
        footer_row = f"<tfoot><tr>{foot_cells}</tr></tfoot>"

    truncation_note = (
        f'<div class="tbl-note">Showing {len(display_rows)} of {row_count} records.</div>'
        if row_count > max_rows else
        f'<div class="tbl-note">{row_count} record{"s" if row_count != 1 else ""}.</div>'
    )

    return f"""
    <div class="tbl-wrap" style="--accent:{accent_color};--accent-bg:{accent_bg};">
      <div class="tbl-header">
        <span class="tbl-title">{safe_title}</span>
        <span class="tbl-badge">{row_count} records</span>
      </div>
      <div class="tbl-scroller">
        <table>
          <thead><tr>{header_cells}</tr></thead>
          <tbody>{body_rows}</tbody>
          {footer_row}
        </table>
      </div>
      {truncation_note}
    </div>"""


def _pretty_key(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _pick_nested(row: dict[str, Any], key: str) -> Any:
    value = row.get(key)
    if value is not None:
        return value

    prefix = f"{key}_"
    nested: dict[str, Any] = {}
    for field, field_value in row.items():
        if field.startswith(prefix):
            nested[field[len(prefix):]] = field_value
    return nested or None


def _build_tax_rows(section_data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for section_name, payload in section_data.items():
        if not isinstance(payload, dict):
            continue
        rows.append(
            {
                "section": _pretty_key(section_name),
                "taxable_value": payload.get("taxable_value", 0),
                "igst": payload.get("igst", 0),
                "cgst": payload.get("cgst", 0),
                "sgst": payload.get("sgst", 0),
                "cess": payload.get("cess", 0),
            }
        )
    return rows


def _render_gstr3b_details_card(
    title: str,
    table_data: dict[str, Any],
    accent_color: str,
    accent_bg: str,
) -> str:
    rows = table_data.get("rows", []) if isinstance(table_data, dict) else []
    if not rows or not isinstance(rows[0], dict):
        return _render_table(title, [], accent_color, accent_bg)

    row = rows[0]
    return_period = row.get("return_period") or row.get("ret_period") or "N/A"

    supply_details = _pick_nested(row, "supply_details")
    inter_state = _pick_nested(row, "inter_state_supplies")

    supply_rows = _build_tax_rows(supply_details if isinstance(supply_details, dict) else {})

    inter_state_rows: list[dict[str, Any]] = []
    if isinstance(inter_state, dict):
        for section_name, section_rows in inter_state.items():
            if not isinstance(section_rows, list):
                continue
            for item in section_rows:
                if not isinstance(item, dict):
                    continue
                inter_state_rows.append(
                    {
                        "category": _pretty_key(section_name),
                        "pos": item.get("pos") or item.get("place_of_supply") or "-",
                        "taxable_value": item.get("taxable_value", 0),
                        "igst": item.get("igst", 0),
                    }
                )

    supply_html = _render_table("Supply Details (3.1)", supply_rows, accent_color, accent_bg, max_rows=20)
    inter_state_html = _render_table(
        "Inter-State Supplies (3.2)",
        inter_state_rows,
        accent_color,
        accent_bg,
        max_rows=40,
    )

    return f"""
    <div class="tbl-wrap" style="--accent:{accent_color};--accent-bg:{accent_bg};">
      <div class="tbl-header">
        <span class="tbl-title">{escape(title)}</span>
        <span class="tbl-badge">Return Period: {escape(str(return_period))}</span>
      </div>
      <div style="display:grid;gap:14px;padding:12px;">
        {supply_html}
        {inter_state_html}
      </div>
    </div>"""


def _render_gstr3b_auto_liability_card(
    title: str,
    table_data: dict[str, Any],
    accent_color: str,
    accent_bg: str,
) -> str:
    rows = table_data.get("rows", []) if isinstance(table_data, dict) else []
    if not rows or not isinstance(rows[0], dict):
        return _render_table(title, [], accent_color, accent_bg)

    row = rows[0]
    liability = _pick_nested(row, "auto_calculated_liability")
    if not isinstance(liability, dict):
        liability = {}

    metadata_rows = [
        {
            "field": "R1 Filed Date",
            "value": liability.get("r1_filed_date") or row.get("auto_calculated_liability_r1_filed_date") or "-",
        },
        {
            "field": "R2B Generated",
            "value": liability.get("r2b_gen_date") or row.get("auto_calculated_liability_r2b_gen_date") or "-",
        },
        {
            "field": "R3B Generated",
            "value": liability.get("r3b_gen_date") or row.get("auto_calculated_liability_r3b_gen_date") or "-",
        },
        {
            "field": "Status Code",
            "value": row.get("status_cd") or "-",
        },
    ]

    supply_details = liability.get("supply_details") if isinstance(liability.get("supply_details"), dict) else {}
    eligible_itc = liability.get("eligible_itc") if isinstance(liability.get("eligible_itc"), dict) else {}
    inter_state = liability.get("inter_state_supplies") if isinstance(liability.get("inter_state_supplies"), dict) else {}

    def _subtotal_rows(block: dict[str, Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for block_name, payload in block.items():
            if not isinstance(payload, dict):
                continue
            subtotal = payload.get("subtotal")
            if isinstance(subtotal, dict):
                out.append(
                    {
                        "section": _pretty_key(block_name),
                        "taxable_value": subtotal.get("taxable_value", 0),
                        "igst": subtotal.get("igst", 0),
                        "cgst": subtotal.get("cgst", 0),
                        "sgst": subtotal.get("sgst", 0),
                        "cess": subtotal.get("cess", 0),
                    }
                )
        return out

    supply_rows = _subtotal_rows(supply_details)
    itc_rows = _subtotal_rows(eligible_itc)

    inter_state_rows: list[dict[str, Any]] = []
    for section_name, payload in inter_state.items():
        if not isinstance(payload, dict):
            continue
        subtotal = payload.get("subtotal")
        if isinstance(subtotal, list):
            for item in subtotal:
                if not isinstance(item, dict):
                    continue
                inter_state_rows.append(
                    {
                        "section": _pretty_key(section_name),
                        "pos": item.get("pos") or item.get("place_of_supply") or "-",
                        "taxable_value": item.get("taxable_value", 0),
                        "igst": item.get("igst", 0),
                    }
                )

    error_list = liability.get("errors")
    if not isinstance(error_list, list):
        error_list = row.get("auto_calculated_liability_errors")
    if not isinstance(error_list, list):
        error_list = []
    error_rows = [{"error": str(err)} for err in error_list]

    metadata_html = _render_table("Auto Liability Metadata", metadata_rows, accent_color, accent_bg, max_rows=10)
    supply_html = _render_table("Supply Detail Subtotals", supply_rows, accent_color, accent_bg, max_rows=20)
    itc_html = _render_table("Eligible ITC Subtotals", itc_rows, accent_color, accent_bg, max_rows=20)
    inter_state_html = _render_table(
        "Inter-State Supply Subtotals",
        inter_state_rows,
        accent_color,
        accent_bg,
        max_rows=40,
    )
    errors_html = _render_table("Auto Liability Errors", error_rows, accent_color, accent_bg, max_rows=20)

    return f"""
    <div class="tbl-wrap" style="--accent:{accent_color};--accent-bg:{accent_bg};">
      <div class="tbl-header">
        <span class="tbl-title">{escape(title)}</span>
        <span class="tbl-badge">Structured View</span>
      </div>
      <div style="display:grid;gap:14px;padding:12px;">
        {metadata_html}
        {supply_html}
        {itc_html}
        {inter_state_html}
        {errors_html}
      </div>
    </div>"""


# ─────────────────────────────────────────────
# MAIN REPORT BUILDER
# ─────────────────────────────────────────────

async def build_monthly_report_html(
    session: AsyncSession,
    *,
    gstin: str,
    year: str,
    month: str,
    tables: list[str] | None = None,
) -> str:
    normalized = normalize_gstins([gstin])
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="GSTIN is required and must be 15 characters.",
        )

    selected_tables = resolve_requested_tables(tables) if tables else REPORT_TABLES
    selected_tables = [t for t in selected_tables if t in REPORT_TABLES]

    dataset = await fetch_business_dataset(
        session,
        gstins=normalized,
        client_ids=None,
        include_inactive=False,
        tables=selected_tables,
        year=year,
        month=month,
    )

    if not dataset.get("clients"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found for the requested GSTIN and period.",
        )

    client = dataset["clients"][0]
    tables_data: dict[str, dict[str, Any]] = client.get("tables", {})
    trade_name = client.get("trade_name") or client.get("legal_name") or normalized[0]
    month_label = _MONTH_NAMES.get(str(month).zfill(2), month)
    period_label = f"{month_label} {year}"

    # ── Build per-table summaries ─────────────────────────────────────
    table_summaries: dict[str, dict[str, Any]] = {}
    table_rows_flat: dict[str, list[dict[str, Any]]] = {}

    for tname in selected_tables:
        td = tables_data.get(tname, {"row_count": 0, "rows": []})
        rows = _flatten_table_rows(tname, td)
        numeric_totals = _aggregate_numeric(rows)
        table_summaries[tname] = {
            "row_count": td.get("row_count", 0),
            "numeric_totals": numeric_totals,
        }
        table_rows_flat[tname] = rows

    # ── Derive headline KPIs ──────────────────────────────────────────
    outward_tables = [
        "gstr1_b2b", "gstr1_b2cs", "gstr1_b2cl", "gstr1_cdnr",
        "gstr1_cdnur", "gstr1_exp", "gstr1_advance_tax", "gstr1_txp",
    ]
    outward_taxable = sum(
        _sum_table_fields(table_summaries, t, ["taxable_value", "total_taxable_value"])
        for t in outward_tables
    )
    outward_tax = sum(
        _sum_table_fields(table_summaries, t, ["igst", "cgst", "sgst", "cess",
                                               "total_igst", "total_cgst", "total_sgst"])
        for t in outward_tables
    )
    itc_available = _sum_table_fields(table_summaries, "gstr2b",
                                      ["igst_amt", "cgst_amt", "sgst_amt", "cess_amt"])
    cash_closing = _sum_table_fields(table_summaries, "ledger_balance",
                                     ["cash_igst_total", "cash_cgst_total",
                                      "cash_sgst_total", "cash_cess_total"])
    itc_closing = _sum_table_fields(table_summaries, "ledger_itc",
                                    ["closing_igst", "closing_cgst",
                                     "closing_sgst", "closing_cess"])
    liability_closing = _sum_table_fields(table_summaries, "ledger_liability",
                                          ["igst_bal", "cgst_bal", "sgst_bal", "cess_bal"])

    # ── Chart 1: Outward supply by category ──────────────────────────
    outward_chart_data: list[tuple[str, Decimal]] = [
        ("B2B", _sum_table_fields(table_summaries, "gstr1_b2b",
                                  ["taxable_value", "total_taxable_value"])),
        ("B2CS", _sum_table_fields(table_summaries, "gstr1_b2cs",
                                   ["taxable_value", "total_taxable_value"])),
        ("B2CL", _sum_table_fields(table_summaries, "gstr1_b2cl",
                                   ["taxable_value", "total_taxable_value"])),
        ("Exports", _sum_table_fields(table_summaries, "gstr1_exp",
                                      ["taxable_value", "total_taxable_value"])),
        ("CDN-R", _sum_table_fields(table_summaries, "gstr1_cdnr",
                                    ["note_value"])),
        ("CDN-UR", _sum_table_fields(table_summaries, "gstr1_cdnur",
                                     ["note_value"])),
        ("Advance", _sum_table_fields(table_summaries, "gstr1_advance_tax",
                                      ["taxable_value"])),
    ]
    chart1_svg = _svg_horizontal_bars(
        outward_chart_data,
        "Outward Supply — Taxable Value by Category",
        color="#1B4FD8",
        width=520,
    )

    # ── Chart 2: Tax component donut ─────────────────────────────────
    tax_igst = _sum_table_fields(table_summaries, "gstr3b_details",
                                 ["ttl_igst"]) or _sum_table_fields(
        table_summaries, "gstr1_b2b", ["igst", "total_igst"])
    tax_cgst = _sum_table_fields(table_summaries, "gstr3b_details",
                                 ["ttl_cgst"]) or _sum_table_fields(
        table_summaries, "gstr1_b2b", ["cgst", "total_cgst"])
    tax_sgst = _sum_table_fields(table_summaries, "gstr3b_details",
                                 ["ttl_sgst"]) or _sum_table_fields(
        table_summaries, "gstr1_b2b", ["sgst", "total_sgst"])
    tax_cess = _sum_table_fields(table_summaries, "gstr3b_details",
                                 ["ttl_cess"]) or _sum_table_fields(
        table_summaries, "gstr1_b2b", ["cess"])

    chart2_svg = _svg_donut(
        [
            ("IGST", tax_igst, "#1B4FD8"),
            ("CGST", tax_cgst, "#7C3AED"),
            ("SGST", tax_sgst, "#0D7490"),
            ("CESS", tax_cess, "#B45309"),
        ],
        "Tax Component Mix",
    )

    # ── Chart 3: Ledger positions grouped bar ────────────────────────
    def _get_cash_row(field: str) -> Decimal:
        return _sum_table_fields(table_summaries, "ledger_balance", [field])

    chart3_svg = _svg_grouped_bars(
        [
            ("Cash", [
                ("IGST", _get_cash_row("cash_igst_total")),
                ("CGST", _get_cash_row("cash_cgst_total")),
                ("SGST", _get_cash_row("cash_sgst_total")),
                ("CESS", _get_cash_row("cash_cess_total")),
            ]),
            ("ITC", [
                ("IGST", _sum_table_fields(table_summaries, "ledger_itc", ["closing_igst"])),
                ("CGST", _sum_table_fields(table_summaries, "ledger_itc", ["closing_cgst"])),
                ("SGST", _sum_table_fields(table_summaries, "ledger_itc", ["closing_sgst"])),
                ("CESS", _sum_table_fields(table_summaries, "ledger_itc", ["closing_cess"])),
            ]),
            ("Liability", [
                ("IGST", _sum_table_fields(table_summaries, "ledger_liability", ["igst_bal"])),
                ("CGST", _sum_table_fields(table_summaries, "ledger_liability", ["cgst_bal"])),
                ("SGST", _sum_table_fields(table_summaries, "ledger_liability", ["sgst_bal"])),
                ("CESS", _sum_table_fields(table_summaries, "ledger_liability", ["cess_bal"])),
            ]),
        ],
        "Ledger Position — Component Breakdown",
        colors=["#1B4FD8", "#7C3AED", "#0D7490", "#B45309"],
        width=520,
    )

    # ── Chart 4 (NEW): Liability vs ITC Available ────────────────────────
    chart4_svg = _svg_horizontal_bars(
        [
            ("Total Liability (Outward)", outward_tax),
            ("Total ITC Available (2B)", itc_available),
        ],
        "Liability vs Input Tax Credit",
        color="#0D7490",
        width=520,
    )

    # ── Chart 5 (NEW): Supply Composition (Donut) ───────────────────────
    b2b_val = _sum_table_fields(table_summaries, "gstr1_b2b", ["taxable_value", "total_taxable_value"])
    b2c_val = _sum_table_fields(table_summaries, "gstr1_b2cs", ["taxable_value", "total_taxable_value"]) + \
              _sum_table_fields(table_summaries, "gstr1_b2cl", ["taxable_value", "total_taxable_value"])
    exp_val = _sum_table_fields(table_summaries, "gstr1_exp", ["taxable_value", "total_taxable_value"])
    
    chart5_svg = _svg_donut(
        [
            ("B2B Supply", b2b_val, "#1B4FD8"),
            ("B2C Supply", b2c_val, "#7C3AED"),
            ("Exports", exp_val, "#0F766E"),
        ],
        "Supply Composition (Taxable Value)",
    )


    # ── Build chapter HTML ────────────────────────────────────────────
    chapters_html = ""
    for ch_idx, (ch_title, ch_tables) in enumerate(TABLE_CHAPTERS.items()):
        accent, accent_bg = CHAPTER_COLORS[ch_idx % len(CHAPTER_COLORS)]
        ch_num = str(ch_idx + 1).zfill(2)

        tables_in_chapter = [t for t in ch_tables if t in selected_tables]
        if not tables_in_chapter:
            continue

        table_blocks = ""
        for tname in tables_in_chapter:
            label = TABLE_LABELS.get(tname, tname)
            rows = table_rows_flat.get(tname, [])
            if tname == "gstr3b_details":
                table_blocks += _render_gstr3b_details_card(label, tables_data.get(tname, {}), accent, accent_bg)
            elif tname == "gstr3b_auto_liability":
                table_blocks += _render_gstr3b_auto_liability_card(label, tables_data.get(tname, {}), accent, accent_bg)
            else:
                table_blocks += _render_table(label, rows, accent, accent_bg)

        chapters_html += f"""
        <section class="chapter">
          <div class="chapter-rule" style="--ch-accent:{accent};--ch-bg:{accent_bg};">
            <div class="chapter-num" style="color:{accent};">{ch_num}</div>
            <div class="chapter-title-wrap">
              <div class="chapter-title">{escape(ch_title)}</div>
              <div class="chapter-sub" style="color:{accent};">
                {len(tables_in_chapter)} table{"s" if len(tables_in_chapter) != 1 else ""} ·
                {sum(table_summaries.get(t, {}).get("row_count", 0) for t in tables_in_chapter)} total records
              </div>
            </div>
          </div>
          <div class="chapter-tables">
            {table_blocks}
          </div>
        </section>"""

    # ── Metric pills HTML ─────────────────────────────────────────────
    metrics = [
        ("Outward Taxable Value", _fmt_currency(outward_taxable), "₹", "#1B4FD8"),
        ("Outward Tax Liability", _fmt_currency(outward_tax), "₹", "#6D28D9"),
        ("ITC Available (2B)", _fmt_currency(itc_available), "₹", "#0D7490"),
        ("Cash Ledger Balance", _fmt_currency(cash_closing), "₹", "#B45309"),
        ("ITC Ledger Closing", _fmt_currency(itc_closing), "₹", "#15803D"),
        ("Return Liability", _fmt_currency(liability_closing), "₹", "#B91C1C"),
    ]

    kpi_html = ""
    for label, value, _, color in metrics:
        kpi_html += f"""
        <div class="kpi-card" style="border-left: 4px solid {color};">
          <div class="kpi-label">{escape(label)}</div>
          <div class="kpi-value" style="color:{color};">{escape(value)}</div>
        </div>"""

    # ── Return status summary ─────────────────────────────────────────
    status_rows = table_rows_flat.get("gst_return_status", [])
    filed_returns = [r for r in status_rows if str(r.get("status", "")).upper() in ("FILED", "SUBMITTED")]
    pending_returns = [r for r in status_rows if str(r.get("status", "")).upper() in ("NOT FILED", "PENDING", "")]
    status_summary_html = ""
    if status_rows:
        status_summary_html = f"""
        <div class="status-summary">
          <div class="status-item status-filed">
            <span class="status-dot"></span>
            <span>{len(filed_returns)} Filed</span>
          </div>
          <div class="status-item status-pending">
            <span class="status-dot"></span>
            <span>{len(pending_returns)} Pending</span>
          </div>
        </div>"""

    total_records = sum(s.get("row_count", 0) for s in table_summaries.values())
    active_tables = sum(1 for s in table_summaries.values() if s.get("row_count", 0) > 0)

    # ═══════════════════════════════════════════════════════════════════
    # FULL HTML DOCUMENT
    # ═══════════════════════════════════════════════════════════════════
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>GST Monthly Report — {escape(normalized[0])} — {escape(period_label)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
  <style>
    :root {{
      --navy:      #00205B; /* Updated matching uploaded color */
      --navy-dark: #00153D;
      --surface:   #F4F7F9;
      --card:      #FFFFFF;
      --gold:      #D4AF37;
      --gold-lt:   #F1E5AC;
      --steel:     #334155;
      --cloud:     #64748B;
      --border:    #E2E8F0;
      --stripe:    #F8FAFC;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: 'IBM Plex Sans', sans-serif;
      background: var(--surface);
      color: var(--steel);
      font-size: 13px;
      line-height: 1.55;
      -webkit-font-smoothing: antialiased;
    }}

    /* ── MASTHEAD ── */
    .masthead {{
      background: var(--navy);
      padding: 0;
      position: relative;
      overflow: hidden;
      border-bottom: 4px solid var(--gold);
    }}
    .masthead-inner {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 44px 40px 36px;
      display: grid;
      grid-template-columns: 1fr auto;
      align-items: end;
      gap: 24px;
      position: relative;
      z-index: 2;
    }}
    .firm-name {{
      font-family: 'Lora', serif;
      font-size: 28px;
      font-weight: 700;
      color: #FFFFFF;
      letter-spacing: 0.5px;
      margin-bottom: 3px;
    }}
    .firm-name span {{
      color: var(--gold-lt);
    }}
    .firm-tagline {{
      font-size: 11px;
      color: rgba(255,255,255,0.6);
      text-transform: uppercase;
      letter-spacing: 2.5px;
      font-weight: 500;
    }}
    .masthead-divider {{
      width: 48px;
      height: 2px;
      background: var(--gold-lt);
      margin: 14px 0;
    }}
    .report-info {{
      font-size: 12px;
      color: rgba(255,255,255,0.7);
      line-height: 1.8;
    }}
    .report-info strong {{
      color: #FFFFFF;
      font-weight: 600;
    }}
    .masthead-right {{
      text-align: right;
    }}
    .period-badge {{
      display: inline-block;
      background: rgba(255,255,255,0.1);
      border: 1px solid rgba(255,255,255,0.2);
      color: #FFFFFF;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 13px;
      font-weight: 600;
      padding: 8px 16px;
      border-radius: 6px;
      letter-spacing: 0.5px;
      margin-bottom: 10px;
    }}
    .gstin-badge {{
      display: block;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11.5px;
      color: rgba(255,255,255,0.5);
      letter-spacing: 1px;
      margin-top: 6px;
    }}
    .masthead-meta-strip {{
      background: rgba(0,0,0,0.2);
      padding: 12px 40px;
      max-width: 100%;
    }}
    .masthead-meta-inner {{
      max-width: 1180px;
      margin: 0 auto;
      display: flex;
      gap: 28px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .meta-chip {{
      font-size: 11px;
      color: rgba(255,255,255,0.5);
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .meta-chip strong {{
      color: #FFFFFF;
      font-weight: 600;
      font-family: 'IBM Plex Mono', monospace;
    }}
    .meta-dot {{
      width: 4px; height: 4px;
      border-radius: 50%;
      background: rgba(255,255,255,0.3);
    }}

    /* ── PAGE WRAPPER ── */
    .page {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 40px 40px 60px;
    }}

    /* ── SECTION LABEL ── */
    .section-label {{
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 2.5px;
      color: var(--cloud);
      margin-bottom: 18px;
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .section-label::after {{
      content: '';
      flex: 1;
      height: 1px;
      background: var(--border);
    }}

    /* ── KPI CARDS ── */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      margin-bottom: 48px;
    }}
    @media (max-width: 860px) {{ .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
    .kpi-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px 24px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
      transition: transform 0.2s, box-shadow 0.2s;
    }}
    .kpi-card:hover {{
      box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
      transform: translateY(-2px);
    }}
    .kpi-label {{
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--cloud);
      margin-bottom: 8px;
    }}
    .kpi-value {{
      font-family: 'IBM Plex Mono', monospace;
      font-size: 20px;
      font-weight: 700;
      line-height: 1.2;
    }}

    /* ── CHARTS GRID ── */
    .charts-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 20px;
      margin-bottom: 48px;
    }}
    .chart-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 24px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
      display: flex;
      justify-content: center;
      align-items: center;
    }}
    .chart-full {{
      grid-column: span 2;
    }}

    /* ── STATUS SUMMARY ── */
    .status-summary {{
      display: flex;
      gap: 16px;
    }}
    .status-item {{
      display: flex;
      align-items: center;
      gap: 7px;
      font-size: 11px;
      font-weight: 600;
      color: #fff;
    }}
    .status-dot {{
      width: 8px; height: 8px;
      border-radius: 50%;
    }}
    .status-filed .status-dot {{ background: #4ADE80; }}
    .status-pending .status-dot {{ background: #F87171; }}

    /* ── CHAPTER DIVIDERS ── */
    .chapter {{
      margin-bottom: 56px;
    }}
    .chapter-rule {{
      display: flex;
      align-items: center;
      gap: 20px;
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 2px solid var(--border);
    }}
    .chapter-num {{
      font-family: 'Lora', serif;
      font-size: 44px;
      font-weight: 700;
      line-height: 1;
      opacity: 0.15;
      flex-shrink: 0;
      width: 54px;
    }}
    .chapter-title {{
      font-family: 'Lora', serif;
      font-size: 22px;
      font-weight: 700;
      color: var(--navy);
      line-height: 1.2;
    }}
    .chapter-sub {{
      font-size: 12px;
      font-weight: 500;
      margin-top: 4px;
      opacity: 0.8;
    }}
    .chapter-tables {{
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}

    /* ── DATA TABLES ── */
    .tbl-wrap {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    }}
    .tbl-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
      background: #FFFFFF;
      border-left: 4px solid var(--accent, #1B4FD8);
    }}
    .tbl-title {{
      font-size: 14px;
      font-weight: 700;
      color: var(--navy);
      font-family: 'IBM Plex Sans', sans-serif;
    }}
    .tbl-badge {{
      background: var(--accent, #1B4FD8);
      color: #fff;
      font-size: 10px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 20px;
      letter-spacing: 0.5px;
      font-family: 'IBM Plex Mono', monospace;
    }}
    .tbl-empty {{
      padding: 24px 20px;
      color: var(--cloud);
      font-size: 12.5px;
      font-style: italic;
      text-align: center;
    }}
    .tbl-scroller {{
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }}
    thead tr {{
      background: var(--stripe);
    }}
    th {{
      padding: 12px 16px;
      font-size: 10.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--steel);
      white-space: nowrap;
      border-bottom: 2px solid var(--border);
      text-align: left;
    }}
    th.num-col {{ text-align: right; }}
    td {{
      padding: 10px 16px;
      border-bottom: 1px solid #F1F5F9;
      color: var(--steel);
      white-space: nowrap;
      max-width: 240px;
      overflow: hidden;
      text-overflow: ellipsis;
      vertical-align: middle;
    }}
    td.num-col {{
      text-align: right;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 11.5px;
      color: #0F172A;
      font-weight: 500;
    }}
    tbody tr:hover td {{
      background: #F8FAFC;
    }}
    tfoot tr {{
      background: var(--stripe);
    }}
    .tbl-total {{
      font-weight: 700;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 12px;
      color: var(--navy);
      border-top: 2px solid var(--border);
      text-align: right;
      padding: 10px 16px;
    }}
    .tbl-note {{
      padding: 10px 20px;
      font-size: 11px;
      color: var(--cloud);
      border-top: 1px solid var(--border);
      background: #FFFFFF;
    }}

    /* ── FOOTER ── */
    .footer {{
      background: var(--navy-dark);
      color: rgba(255,255,255,0.7);
      border-top: 4px solid var(--gold);
    }}
    .footer-inner {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 48px 40px 32px;
    }}
    .footer-grid {{
      display: grid;
      grid-template-columns: 1.5fr 1fr 1fr 1fr;
      gap: 32px;
      padding-bottom: 32px;
      border-bottom: 1px solid rgba(255,255,255,0.1);
      margin-bottom: 24px;
    }}
    .footer-brand {{
      font-family: 'Lora', serif;
      font-size: 20px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 6px;
    }}
    .footer-brand span {{ color: var(--gold-lt); }}
    .footer-tagline {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 2px;
      color: rgba(255,255,255,0.4);
      margin-bottom: 16px;
    }}
    .footer-contact {{
      font-size: 12px;
      color: rgba(255,255,255,0.6);
      line-height: 2;
    }}
    .footer-contact a {{
      color: var(--gold-lt);
      text-decoration: none;
    }}
    .footer-city-title {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: var(--gold-lt);
      margin-bottom: 10px;
    }}
    .footer-address {{
      font-size: 12px;
      color: rgba(255,255,255,0.5);
      line-height: 1.8;
    }}
    .footer-bottom {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .footer-nav {{
      display: flex;
      gap: 24px;
      font-size: 12px;
      color: rgba(255,255,255,0.5);
    }}
    .footer-nav span {{
      cursor: default;
      transition: color 0.15s;
    }}
    .footer-nav span:hover {{ color: rgba(255,255,255,0.9); }}
    .footer-copy {{
      font-size: 11px;
      color: rgba(255,255,255,0.3);
    }}

    /* ── PRINT ── */
    @media print {{
      body {{ background: white; }}
      .masthead {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
      .kpi-card, .chart-card, .tbl-wrap {{ break-inside: avoid; box-shadow: none; border: 1px solid #CCC; }}
      .chapter {{ break-before: auto; }}
    }}
  </style>
</head>
<body>

<header class="masthead">
  <div class="masthead-inner">
    <div>
      <div class="firm-name">P.G. Joshi <span>&amp;</span> Co.</div>
      <div class="firm-tagline">Chartered Accountants</div>
      <div class="masthead-divider"></div>
      <div class="report-info">
        <strong>GST Monthly Compliance Report</strong><br/>
        Prepared for &nbsp;<strong>{escape(trade_name)}</strong><br/>
        GSTIN: &nbsp;<strong style="font-family:'IBM Plex Mono',monospace;letter-spacing:1px;">{escape(normalized[0])}</strong>
      </div>
    </div>
    <div class="masthead-right">
      <div class="period-badge">{escape(period_label)}</div>
      <div class="gstin-badge">Tax Period Report</div>
    </div>
  </div>
  <div class="masthead-meta-strip">
    <div class="masthead-meta-inner">
      <div class="meta-chip"><span>Tables fetched</span><strong>{len(selected_tables)}</strong></div>
      <div class="meta-dot"></div>
      <div class="meta-chip"><span>Active tables</span><strong>{active_tables}</strong></div>
      <div class="meta-dot"></div>
      <div class="meta-chip"><span>Total records</span><strong>{total_records:,}</strong></div>
      <div class="meta-dot"></div>
      <div class="meta-chip"><span>Report generated</span><strong style="font-family:'IBM Plex Mono',monospace;">{escape(period_label)}</strong></div>
      {status_summary_html}
    </div>
  </div>
</header>

<div class="page">

  <div class="section-label">Executive Summary — Key Financial Indicators</div>
  <div class="kpi-grid">
    {kpi_html}
  </div>

  <div class="section-label">Analytics — Visual Insights</div>
  <div class="charts-grid">
    <div class="chart-card">
      {chart1_svg}
    </div>
    <div class="chart-card">
      {chart5_svg}
    </div>
    <div class="chart-card">
      {chart4_svg}
    </div>
    <div class="chart-card">
      {chart2_svg}
    </div>
    <div class="chart-card chart-full">
      {chart3_svg}
    </div>
  </div>

  <div class="section-label">Full Data Drill-Down — All Tables</div>
  {chapters_html}

</div>

<footer class="footer">
  <div class="footer-inner">
    <div class="footer-grid">
      <div>
        <div class="footer-brand">P.G. Joshi <span>&amp;</span> Co.</div>
        <div class="footer-tagline">Chartered Accountants</div>
        <div class="footer-contact">
          <div>Phone: <a href="tel:07122524309">0712-2524309</a></div>
          <div>Email: <a href="mailto:info@pgjco.com">info@pgjco.com</a></div>
          <div style="margin-top:12px;font-size:11px;color:rgba(255,255,255,0.4);">
            GSTIN: {escape(normalized[0])} &nbsp;·&nbsp; {escape(period_label)}
          </div>
        </div>
      </div>
      <div>
        <div class="footer-city-title">Nagpur</div>
        <div class="footer-address">Dhanwate Chambers, Pt. Malviya Road, Sitabuldi, Nagpur, Maharashtra 440012</div>
      </div>
      <div>
        <div class="footer-city-title">Mumbai</div>
        <div class="footer-address">C7, Ultra Co-op. Hsg. Society, Lt. Dilip Gupte Marg, Mahim West, Mumbai 400 016</div>
      </div>
      <div>
        <div class="footer-city-title">Pune</div>
        <div class="footer-address">Flat No.6, Janhavi Apartments, CTS No. 40/22, Shantabai Kalmadi Path, Erandwane, Pune 411004</div>
      </div>
    </div>
    <div class="footer-bottom">
      <div class="footer-nav">
        <span>About Us</span>
        <span>Services</span>
        <span>Blogs</span>
        <span>Alumni Connect</span>
      </div>
      <div class="footer-copy">© 2023–2025 P.G. Joshi &amp; Co. Chartered Accountants — All Rights Reserved</div>
    </div>
  </div>
</footer>

</body>
</html>"""