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


def persist_ledger_balance(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    if not result or (not result.get("success") and result.get("status_cd") is None):
        return

    cash_balance = as_dict(result.get("cash_balance"))
    igst = as_dict(cash_balance.get("igst"))
    cgst = as_dict(cash_balance.get("cgst"))
    sgst = as_dict(cash_balance.get("sgst"))
    cess = as_dict(cash_balance.get("cess"))
    itc_balance = as_dict(result.get("itc_balance"))
    blocked_balance = as_dict(result.get("itc_blocked_balance"))

    async def work(session) -> None:
        gstin = sentinel(kwargs.get("gstin") or get_arg(args, 0) or result.get("gstin"))
        year = sentinel(kwargs.get("year") or get_arg(args, 1))
        month = sentinel(kwargs.get("month") or get_arg(args, 2))
        if not gstin:
            return

        client_id = await ensure_client(session, gstin)
        await upsert_row(
            session,
            "ledger_balance",
            {
                "client_id": client_id,
                "year": year,
                "month": month,
                "status_cd": result.get("status_cd"),
                "cash_igst_tax": to_float(igst.get("tax")),
                "cash_igst_interest": to_float(igst.get("interest")),
                "cash_igst_penalty": to_float(igst.get("penalty")),
                "cash_igst_fee": to_float(igst.get("fee")),
                "cash_igst_other": to_float(igst.get("other")),
                "cash_igst_total": to_float(igst.get("total")),
                "cash_cgst_total": to_float(cgst.get("total")),
                "cash_sgst_total": to_float(sgst.get("total")),
                "cash_cess_total": to_float(cess.get("total")),
                "itc_igst": to_float(itc_balance.get("igst")),
                "itc_cgst": to_float(itc_balance.get("cgst")),
                "itc_sgst": to_float(itc_balance.get("sgst")),
                "itc_cess": to_float(itc_balance.get("cess")),
                "itc_blocked_igst": to_float(blocked_balance.get("igst")),
                "itc_blocked_cgst": to_float(blocked_balance.get("cgst")),
                "itc_blocked_sgst": to_float(blocked_balance.get("sgst")),
                "itc_blocked_cess": to_float(blocked_balance.get("cess")),
                "upstream_status_code": result.get("upstream_status_code"),
            },
        )

    run_async(lambda: run_in_session(work))


def persist_ledger_cash(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    if not result or (not result.get("success") and result.get("status_cd") is None):
        return

    async def work(session) -> None:
        gstin = sentinel(kwargs.get("gstin") or get_arg(args, 0) or result.get("gstin"))
        from_date = sentinel(kwargs.get("from_date") or get_arg(args, 1) or result.get("from_date"))
        to_date = sentinel(kwargs.get("to_date") or get_arg(args, 2) or result.get("to_date"))
        if not gstin or not from_date or not to_date:
            return

        client_id = await ensure_client(session, gstin)
        await upsert_row(
            session,
            "ledger_cash",
            {
                "client_id": client_id,
                "from_date": from_date,
                "to_date": to_date,
                "status_cd": result.get("status_cd"),
                "opening_balance": as_dict(result.get("opening_balance")) or None,
                "closing_balance": as_dict(result.get("closing_balance")) or None,
                "transactions": as_list(result.get("transactions")),
                "upstream_status_code": result.get("upstream_status_code"),
            },
        )

    run_async(lambda: run_in_session(work))


def persist_ledger_itc(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    if not result or (not result.get("success") and result.get("status_cd") is None):
        return

    opening = as_dict(result.get("opening_balance"))
    closing = as_dict(result.get("closing_balance"))
    provisional = result.get("provisional_credit_balances")
    if isinstance(provisional, list):
        provisional = {"items": provisional}
    else:
        provisional = as_dict(provisional) or None

    async def work(session) -> None:
        gstin = sentinel(kwargs.get("gstin") or get_arg(args, 0) or result.get("gstin"))
        from_date = sentinel(kwargs.get("from_date") or get_arg(args, 1) or result.get("from_date"))
        to_date = sentinel(kwargs.get("to_date") or get_arg(args, 2) or result.get("to_date"))
        if not gstin or not from_date or not to_date:
            return

        client_id = await ensure_client(session, gstin)
        await upsert_row(
            session,
            "ledger_itc",
            {
                "client_id": client_id,
                "from_date": from_date,
                "to_date": to_date,
                "status_cd": result.get("status_cd"),
                "opening_igst": to_float(opening.get("igst")),
                "opening_cgst": to_float(opening.get("cgst")),
                "opening_sgst": to_float(opening.get("sgst")),
                "opening_cess": to_float(opening.get("cess")),
                "opening_total_range_balance": to_float(opening.get("total_range_balance")),
                "closing_igst": to_float(closing.get("igst")),
                "closing_cgst": to_float(closing.get("cgst")),
                "closing_sgst": to_float(closing.get("sgst")),
                "closing_cess": to_float(closing.get("cess")),
                "closing_total_range_balance": to_float(closing.get("total_range_balance")),
                "transactions": as_list(result.get("transactions")),
                "provisional_credit_balances": provisional,
                "upstream_status_code": result.get("upstream_status_code"),
            },
        )

    run_async(lambda: run_in_session(work))


def persist_ledger_liability(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    if not result or (not result.get("success") and result.get("status_cd") is None):
        return

    async def work(session) -> None:
        gstin = sentinel(kwargs.get("gstin") or get_arg(args, 0) or result.get("gstin"))
        year = sentinel(kwargs.get("year") or get_arg(args, 1))
        month = sentinel(kwargs.get("month") or get_arg(args, 2))
        from_date = sentinel(kwargs.get("from_date") or get_arg(args, 3) or result.get("from_date"))
        to_date = sentinel(kwargs.get("to_date") or get_arg(args, 4) or result.get("to_date"))
        if not gstin or not year or not month or not from_date or not to_date:
            return

        client_id = await ensure_client(session, gstin)
        await upsert_row(
            session,
            "ledger_liability",
            {
                "client_id": client_id,
                "year": year,
                "month": month,
                "from_date": from_date,
                "to_date": to_date,
                "status_cd": result.get("status_cd"),
                "closing_balance": as_dict(result.get("closing_balance")) or None,
                "transactions": as_list(result.get("transactions")),
                "upstream_status_code": result.get("upstream_status_code"),
            },
        )

    run_async(lambda: run_in_session(work))


def get_arg(args: tuple[Any, ...], index: int) -> Any:
    return args[index] if len(args) > index else None


LEDGER_PERSISTERS = {
    "get_cash_itc_balance": persist_ledger_balance,
    "get_cash_ledger": persist_ledger_cash,
    "get_itc_ledger": persist_ledger_itc,
    "get_return_liability_ledger": persist_ledger_liability,
}
