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
    to_int,
    upsert_row,
)


def persist_gstr9_auto_calculated(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    result: dict[str, Any],
) -> None:
    if not result or (not result.get("success") and result.get("status_cd") is None):
        return

    async def work(session) -> None:
        gstin = sentinel(kwargs.get("gstin") or get_arg(args, 0) or result.get("gstin"))
        financial_year = sentinel(kwargs.get("financial_year") or get_arg(args, 1))
        if not gstin or not financial_year:
            return

        client_id = await ensure_client(session, gstin)
        await upsert_row(
            session,
            "gstr9_auto_calculated",
            {
                "client_id": client_id,
                "financial_year": financial_year,
                "status_cd": result.get("status_cd"),
                "financial_period": result.get("financial_period"),
                "aggregate_turnover": to_float(result.get("aggregate_turnover")),
                "hsn_min_length": to_int(result.get("hsn_min_length")),
                "table4_outward_supplies": as_dict(result.get("table4_outward_supplies")) or None,
                "table5_exempt_nil_non_gst": as_dict(result.get("table5_exempt_nil_non_gst")) or None,
                "table6_itc_availed": as_dict(result.get("table6_itc_availed")) or None,
                "table8_itc_as_per_2b": as_dict(result.get("table8_itc_as_per_2b")) or None,
                "table9_tax_paid": as_dict(result.get("table9_tax_paid")) or None,
                "upstream_status_code": result.get("upstream_status_code"),
            },
        )

    run_async(lambda: run_in_session(work))


def persist_gstr9_table8a(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    if not result or (not result.get("success") and result.get("status_cd") is None):
        return

    summary = as_dict(result.get("summary"))
    summary_b2b = as_dict(summary.get("b2b"))

    async def work(session) -> None:
        gstin = sentinel(kwargs.get("gstin") or get_arg(args, 0) or result.get("gstin"))
        financial_year = sentinel(kwargs.get("financial_year") or get_arg(args, 1) or result.get("financial_year"))
        if not gstin or not financial_year:
            return

        client_id = await ensure_client(session, gstin)
        file_number = kwargs.get("file_number")
        if file_number is None:
            file_number = get_arg(args, 2)
        if file_number is None:
            file_number = result.get("file_number")

        await upsert_row(
            session,
            "gstr9_table8a",
            {
                "client_id": client_id,
                "financial_year": financial_year,
                "file_number": sentinel(file_number),
                "status_cd": result.get("status_cd"),
                "b2b": as_list(result.get("b2b")),
                "b2ba": as_list(result.get("b2ba")),
                "cdn": as_list(result.get("cdn")),
                "summary_b2b_taxable_value": to_float(summary_b2b.get("taxable_value")),
                "summary_b2b_igst": to_float(summary_b2b.get("igst")),
                "summary_b2b_cgst": to_float(summary_b2b.get("cgst")),
                "summary_b2b_sgst": to_float(summary_b2b.get("sgst")),
                "summary_b2b_cess": to_float(summary_b2b.get("cess")),
                "summary_b2b_invoice_count": to_int(summary_b2b.get("invoice_count")),
                "upstream_status_code": result.get("upstream_status_code"),
            },
        )

    run_async(lambda: run_in_session(work))


def persist_gstr9_details(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    if not result or (not result.get("success") and result.get("status_cd") is None):
        return

    async def work(session) -> None:
        gstin = sentinel(kwargs.get("gstin") or get_arg(args, 0) or result.get("gstin"))
        financial_year = sentinel(kwargs.get("financial_year") or get_arg(args, 1))
        if not gstin or not financial_year:
            return

        client_id = await ensure_client(session, gstin)
        detail_sections = {
            "aggregate_turnover": result.get("aggregate_turnover"),
            "table4_outward_taxable_supplies": as_dict(result.get("table4_outward_taxable_supplies")),
            "table5_exempt_nil_non_gst": as_dict(result.get("table5_exempt_nil_non_gst")),
            "table6_itc_availed": as_dict(result.get("table6_itc_availed")),
            "table7_itc_reversed": as_dict(result.get("table7_itc_reversed")),
            "table8_itc_comparison": as_dict(result.get("table8_itc_comparison")),
            "table9_tax_payable_vs_paid": as_dict(result.get("table9_tax_payable_vs_paid")),
            "table10_turnover_reconciliation": as_dict(result.get("table10_turnover_reconciliation")),
            "table17_hsn_summary": as_dict(result.get("table17_hsn_summary")),
        }
        await upsert_row(
            session,
            "gstr9_details",
            {
                "client_id": client_id,
                "financial_year": financial_year,
                "status_cd": result.get("status_cd"),
                "detail_sections": detail_sections,
                "upstream_status_code": result.get("upstream_status_code"),
            },
        )

    run_async(lambda: run_in_session(work))


def get_arg(args: tuple[Any, ...], index: int) -> Any:
    return args[index] if len(args) > index else None


GSTR9_PERSISTERS = {
    "get_gstr9_auto_calculated": persist_gstr9_auto_calculated,
    "get_gstr9_table8a": persist_gstr9_table8a,
    "get_gstr9_details": persist_gstr9_details,
}
