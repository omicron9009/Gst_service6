from __future__ import annotations

from typing import Any

from .persistence_common import (
    as_dict,
    as_list,
    ensure_client,
    run_async,
    run_in_session,
    sentinel,
    to_float,
    upsert_row,
)


def persist_gstr2a_b2b(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    persist_simple_records(args, kwargs, result, "gstr2a_b2b")


def persist_gstr2a_b2ba(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    persist_simple_records(
        args,
        kwargs,
        result,
        "gstr2a_b2ba",
        extra={
            "filter_counterparty_gstin": sentinel(
                kwargs.get("counterparty_gstin") or get_arg(args, 3)
            ),
        },
    )


def persist_gstr2a_cdn(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    persist_simple_records(
        args,
        kwargs,
        result,
        "gstr2a_cdn",
        extra={
            "filter_counterparty_gstin": sentinel(
                kwargs.get("counterparty_gstin") or get_arg(args, 3)
            ),
            "filter_from_date": sentinel(kwargs.get("from_date") or get_arg(args, 4)),
        },
    )


def persist_gstr2a_cdna(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    persist_simple_records(
        args,
        kwargs,
        result,
        "gstr2a_cdna",
        extra={
            "filter_counterparty_gstin": sentinel(
                kwargs.get("counterparty_gstin") or get_arg(args, 3)
            ),
        },
    )


def persist_gstr2a_document(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    if not result.get("success"):
        return

    summary = as_dict(result.get("summary"))

    async def work(session) -> None:
        gstin, year, month = base_period_args(args, kwargs)
        client_id = await ensure_client(session, gstin)
        await upsert_row(
            session,
            "gstr2a_document",
            {
                "client_id": client_id,
                "year": year,
                "month": month,
                "b2b": as_list(result.get("b2b")),
                "b2ba": as_list(result.get("b2ba")),
                "cdn": as_list(result.get("cdn")),
                "summary_all": as_dict(summary.get("all")) or None,
                "summary_pending_action": as_dict(summary.get("pending_action")) or None,
                "upstream_status_code": result.get("upstream_status_code"),
            },
        )

    run_async(lambda: run_in_session(work))


def persist_gstr2a_isd(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    persist_simple_records(
        args,
        kwargs,
        result,
        "gstr2a_isd",
        extra={
            "filter_counterparty_gstin": sentinel(
                kwargs.get("counterparty_gstin") or get_arg(args, 3)
            ),
        },
    )


def persist_gstr2a_tds(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    if not result.get("success"):
        return

    grand_totals = as_dict(result.get("grand_totals"))

    async def work(session) -> None:
        gstin, year, month = base_period_args(args, kwargs)
        client_id = await ensure_client(session, gstin)
        await upsert_row(
            session,
            "gstr2a_tds",
            {
                "client_id": client_id,
                "year": year,
                "month": month,
                "entry_count": result.get("entry_count"),
                "grand_total_deduction_base": to_float(grand_totals.get("deduction_base_amount")),
                "grand_total_igst": to_float(grand_totals.get("igst")),
                "grand_total_cgst": to_float(grand_totals.get("cgst")),
                "grand_total_sgst": to_float(grand_totals.get("sgst")),
                "grand_total_tds_credit": to_float(grand_totals.get("total_tds_credit")),
                "tds_entries": as_list(result.get("tds")),
                "upstream_status_code": result.get("upstream_status_code"),
            },
        )

    run_async(lambda: run_in_session(work))


def persist_simple_records(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    result: dict[str, Any],
    table_name: str,
    extra: dict[str, Any] | None = None,
) -> None:
    if not result.get("success"):
        return

    async def work(session) -> None:
        gstin, year, month = base_period_args(args, kwargs)
        client_id = await ensure_client(session, gstin)
        values = {
            "client_id": client_id,
            "year": year,
            "month": month,
            "records": as_list(result.get("records")),
            "upstream_status_code": result.get("upstream_status_code"),
        }
        if extra:
            values.update(extra)
        await upsert_row(session, table_name, values)

    run_async(lambda: run_in_session(work))


def base_period_args(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[str, str, str]:
    return (
        sentinel(kwargs.get("gstin") or get_arg(args, 0)),
        sentinel(kwargs.get("year") or get_arg(args, 1)),
        sentinel(kwargs.get("month") or get_arg(args, 2)),
    )


def get_arg(args: tuple[Any, ...], index: int) -> Any:
    return args[index] if len(args) > index else None


GSTR2A_PERSISTERS = {
    "get_gstr2a_b2b": persist_gstr2a_b2b,
    "get_gstr2a_b2ba": persist_gstr2a_b2ba,
    "get_gstr2a_cdn": persist_gstr2a_cdn,
    "get_gstr2a_cdna": persist_gstr2a_cdna,
    "get_gstr2a_document": persist_gstr2a_document,
    "get_gstr2a_isd": persist_gstr2a_isd,
    "get_gstr2a_tds": persist_gstr2a_tds,
}
