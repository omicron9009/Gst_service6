from __future__ import annotations

from typing import Any

from .persistence_common import (
    as_dict,
    ensure_client,
    run_async,
    run_in_session,
    sentinel,
    upsert_row,
)


def persist_gstr2b(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    if not result.get("success"):
        return

    async def work(session) -> None:
        gstin = sentinel(kwargs.get("gstin") or get_arg(args, 0) or result.get("gstin"))
        year = sentinel(kwargs.get("year") or get_arg(args, 1))
        month = sentinel(kwargs.get("month") or get_arg(args, 2))
        client_id = await ensure_client(session, gstin)

        file_number = kwargs.get("file_number")
        if file_number is None:
            file_number = get_arg(args, 3)
        if file_number is None:
            file_number = result.get("file_number")

        await upsert_row(
            session,
            "gstr2b",
            {
                "client_id": client_id,
                "year": year,
                "month": month,
                "file_number": sentinel(file_number),
                "response_type": result.get("response_type") or (
                    "pagination_required" if result.get("pagination_required") else "documents"
                ),
                "return_period": result.get("return_period"),
                "gen_date": result.get("gen_date"),
                "version": result.get("version"),
                "checksum": result.get("checksum"),
                "file_count": result.get("file_count"),
                "pagination_required": bool(result.get("pagination_required")),
                "counterparty_summary": as_dict(result.get("counterparty_summary")) or None,
                "itc_summary": as_dict(result.get("itc_summary")) or None,
                "b2b": as_dict(result.get("b2b")) or None,
                "b2ba": as_dict(result.get("b2ba")) or None,
                "cdnr": as_dict(result.get("cdnr")) or None,
                "cdnra": as_dict(result.get("cdnra")) or None,
                "isd": as_dict(result.get("isd")) or None,
                "grand_summary": as_dict(result.get("grand_summary")) or None,
                "upstream_status_code": result.get("upstream_status_code"),
            },
        )

    run_async(lambda: run_in_session(work))


def persist_gstr2b_regen_status(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    result: dict[str, Any],
) -> None:
    if not result or (not result.get("success") and result.get("raw") is None):
        return

    async def work(session) -> None:
        gstin = sentinel(kwargs.get("gstin") or get_arg(args, 0))
        reference_id = sentinel(kwargs.get("reference_id") or get_arg(args, 1))
        if not gstin or not reference_id:
            return

        client_id = await ensure_client(session, gstin)
        error_report = {
            "regeneration_status": result.get("regeneration_status"),
            "error_code": result.get("error_code"),
            "error_message": result.get("error_message"),
        }
        if not any(error_report.values()):
            error_report = {}

        await upsert_row(
            session,
            "gstr2b_regen_status",
            {
                "client_id": client_id,
                "reference_id": reference_id,
                "form_type_label": result.get("form_type_label"),
                "action": result.get("action"),
                "processing_status_label": result.get("regeneration_status_label"),
                "has_errors": bool(result.get("error_code") or result.get("error_message")),
                "error_report": error_report or None,
                "upstream_status_code": result.get("upstream_status_code"),
            },
        )

    run_async(lambda: run_in_session(work))


def get_arg(args: tuple[Any, ...], index: int) -> Any:
    return args[index] if len(args) > index else None


GSTR2B_PERSISTERS = {
    "get_gstr2b": persist_gstr2b,
    "get_gstr2b_regeneration_status": persist_gstr2b_regen_status,
}
