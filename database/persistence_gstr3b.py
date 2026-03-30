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


def persist_gstr3b_details(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    if not result or (not result.get("success") and result.get("status_cd") is None):
        return

    async def work(session) -> None:
        gstin = sentinel(kwargs.get("gstin") or get_arg(args, 0) or result.get("gstin"))
        year = sentinel(kwargs.get("year") or get_arg(args, 1))
        month = sentinel(kwargs.get("month") or get_arg(args, 2))
        if not gstin:
            return

        client_id = await ensure_client(session, gstin)
        await upsert_row(
            session,
            "gstr3b_details",
            {
                "client_id": client_id,
                "year": year,
                "month": month,
                "status_cd": result.get("status_cd"),
                "return_period": result.get("return_period"),
                "supply_details": as_dict(result.get("supply_details")),
                "inter_state_supplies": as_dict(result.get("inter_state_supplies")),
                "eligible_itc": as_dict(result.get("eligible_itc")),
                "inward_supplies": result.get("inward_supplies") or {},
                "interest_and_late_fee": as_dict(result.get("interest_and_late_fee")),
                "tax_payment": as_dict(result.get("tax_payment")),
                "upstream_status_code": result.get("upstream_status_code"),
            },
        )

    run_async(lambda: run_in_session(work))


def persist_gstr3b_auto_liability(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    result: dict[str, Any],
) -> None:
    if not result or (not result.get("success") and result.get("status_cd") is None):
        return

    async def work(session) -> None:
        gstin = sentinel(kwargs.get("gstin") or get_arg(args, 0) or result.get("gstin"))
        year = sentinel(kwargs.get("year") or get_arg(args, 1))
        month = sentinel(kwargs.get("month") or get_arg(args, 2))
        if not gstin:
            return

        client_id = await ensure_client(session, gstin)
        payload = {
            "r1_filed_date": result.get("r1_filed_date"),
            "r2b_gen_date": result.get("r2b_gen_date"),
            "r3b_gen_date": result.get("r3b_gen_date"),
            "errors": result.get("errors") or [],
            "eligible_itc": as_dict(result.get("eligible_itc")),
            "supply_details": as_dict(result.get("supply_details")),
            "inter_state_supplies": as_dict(result.get("inter_state_supplies")),
        }
        await upsert_row(
            session,
            "gstr3b_auto_liability",
            {
                "client_id": client_id,
                "year": year,
                "month": month,
                "status_cd": result.get("status_cd"),
                "auto_calculated_liability": payload if any(payload.values()) else {},
                "upstream_status_code": result.get("upstream_status_code"),
            },
        )

    run_async(lambda: run_in_session(work))


def get_arg(args: tuple[Any, ...], index: int) -> Any:
    return args[index] if len(args) > index else None


GSTR3B_PERSISTERS = {
    "get_gstr3b_details": persist_gstr3b_details,
    "get_gstr3b_auto_liability": persist_gstr3b_auto_liability,
}
