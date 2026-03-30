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


def persist_gst_return_status(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    result: dict[str, Any],
) -> None:
    if not result or (not result.get("success") and result.get("status_cd") is None):
        return

    async def work(session) -> None:
        gstin = sentinel(kwargs.get("gstin") or get_arg(args, 0))
        year = sentinel(kwargs.get("year") or get_arg(args, 1))
        month = sentinel(kwargs.get("month") or get_arg(args, 2))
        reference_id = sentinel(kwargs.get("reference_id") or get_arg(args, 3))
        if not gstin or not year or not month or not reference_id:
            return

        client_id = await ensure_client(session, gstin)
        error_report = result.get("error_report")
        if error_report is None and (result.get("error_code") or result.get("message")):
            error_report = {
                "error_code": result.get("error_code"),
                "error_message": result.get("message"),
            }

        await upsert_row(
            session,
            "gst_return_status",
            {
                "client_id": client_id,
                "year": year,
                "month": month,
                "reference_id": reference_id,
                "status_cd": result.get("status_cd"),
                "form_type": result.get("form_type"),
                "form_type_label": result.get("form_type_label"),
                "action": result.get("action"),
                "processing_status": result.get("processing_status"),
                "processing_status_label": result.get("processing_status_label"),
                "has_errors": result.get("has_errors")
                if result.get("has_errors") is not None
                else bool(error_report),
                "error_report": as_dict(error_report) or None,
                "upstream_status_code": result.get("upstream_status_code"),
            },
        )

    run_async(lambda: run_in_session(work))


def get_arg(args: tuple[Any, ...], index: int) -> Any:
    return args[index] if len(args) > index else None


RETURN_STATUS_PERSISTERS = {
    "get_gst_return_status": persist_gst_return_status,
}
