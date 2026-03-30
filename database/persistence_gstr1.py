from __future__ import annotations

from typing import Any

from .persistence_common import (
    as_dict,
    as_list,
    result_to_dict,
    run_async,
    run_in_session,
    sentinel,
    upsert_row,
)


def persist_gstr1_advance_tax(args: tuple[Any, ...], kwargs: dict[str, Any], raw_result: Any) -> None:
    result = result_to_dict(raw_result)
    data = as_dict(result.get("data"))
    parsed = as_list(data.get("parsed"))
    if not result.get("success"):
        return

    async def work(session) -> None:
        gstin, year, month = base_period_args(args, kwargs)
        await upsert_period_records(
            session,
            table_name="gstr1_advance_tax",
            gstin=gstin,
            year=year,
            month=month,
            upstream_status_code=result.get("upstream_status_code"),
            records=parsed,
        )

    run_async(lambda: run_in_session(work))


def persist_gstr1_b2b(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    if not result.get("success"):
        return

    summary = as_dict(result.get("summary"))
    invoices = as_list(result.get("invoices"))

    async def work(session) -> None:
        gstin, year, month = base_period_args(args, kwargs)
        await upsert_period_records(
            session,
            table_name="gstr1_b2b",
            gstin=gstin,
            year=year,
            month=month,
            upstream_status_code=result.get("upstream_status_code"),
            extra={
                "filter_action_required": sentinel(kwargs.get("action_required") or get_arg(args, 3)),
                "filter_from_date": sentinel(kwargs.get("from_date") or get_arg(args, 4)),
                "filter_counterparty_gstin": sentinel(
                    kwargs.get("counterparty_gstin") or get_arg(args, 5)
                ),
                "total_invoices": summary.get("total_invoices"),
                "total_taxable_value": summary.get("total_taxable_value"),
                "total_cgst": summary.get("total_cgst"),
                "total_sgst": summary.get("total_sgst"),
                "total_igst": summary.get("total_igst"),
                "invoices": invoices,
            },
        )

    run_async(lambda: run_in_session(work))


def persist_gstr1_summary(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    if not result.get("success"):
        return

    async def work(session) -> None:
        gstin, year, month = base_period_args(args, kwargs)
        await upsert_period_records(
            session,
            table_name="gstr1_summary",
            gstin=gstin,
            year=year,
            month=month,
            upstream_status_code=result.get("upstream_status_code"),
            extra={
                "summary_type": sentinel(kwargs.get("summary_type") or get_arg(args, 3) or "short") or "short",
                "ret_period": result.get("ret_period"),
                "sections": as_list(result.get("sections")),
            },
        )

    run_async(lambda: run_in_session(work))


def persist_gstr1_b2csa(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    persist_simple_records(args, kwargs, result, "gstr1_b2csa")


def persist_gstr1_b2cs(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    persist_simple_records(args, kwargs, result, "gstr1_b2cs")


def persist_gstr1_cdnr(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    if not result.get("success"):
        return

    async def work(session) -> None:
        gstin, year, month = base_period_args(args, kwargs)
        await upsert_period_records(
            session,
            table_name="gstr1_cdnr",
            gstin=gstin,
            year=year,
            month=month,
            upstream_status_code=result.get("upstream_status_code"),
            extra={
                "filter_action_required": sentinel(kwargs.get("action_required") or get_arg(args, 3)),
                "filter_from_date": sentinel(kwargs.get("from_date") or get_arg(args, 4)),
                "record_count": result.get("record_count") or len(as_list(result.get("records"))),
                "records": as_list(result.get("records")),
            },
        )

    run_async(lambda: run_in_session(work))


def persist_gstr1_doc_issue(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    persist_simple_records(args, kwargs, result, "gstr1_doc_issue")


def persist_gstr1_hsn(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    persist_simple_records(args, kwargs, result, "gstr1_hsn")


def persist_gstr1_nil(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    persist_simple_records(args, kwargs, result, "gstr1_nil")


def persist_gstr1_b2cl(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    persist_simple_records(args, kwargs, result, "gstr1_b2cl")


def persist_gstr1_cdnur(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    persist_simple_records(args, kwargs, result, "gstr1_cdnur")


def persist_gstr1_exp(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    persist_simple_records(args, kwargs, result, "gstr1_exp")


def persist_gstr1_txp(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    if not result.get("success"):
        return

    async def work(session) -> None:
        gstin, year, month = base_period_args(args, kwargs)
        await upsert_period_records(
            session,
            table_name="gstr1_txp",
            gstin=gstin,
            year=year,
            month=month,
            upstream_status_code=result.get("upstream_status_code"),
            extra={
                "filter_counterparty_gstin": sentinel(
                    kwargs.get("counterparty_gstin") or get_arg(args, 3)
                ),
                "filter_action_required": sentinel(
                    kwargs.get("action_required") or get_arg(args, 4)
                ),
                "filter_from_date": sentinel(kwargs.get("from_date") or get_arg(args, 5)),
                "records": as_list(result.get("txpd")),
            },
        )

    run_async(lambda: run_in_session(work))


def persist_simple_records(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    result: dict[str, Any],
    table_name: str,
) -> None:
    if not result.get("success"):
        return

    async def work(session) -> None:
        gstin, year, month = base_period_args(args, kwargs)
        await upsert_period_records(
            session,
            table_name=table_name,
            gstin=gstin,
            year=year,
            month=month,
            upstream_status_code=result.get("upstream_status_code"),
            extra={"records": as_list(result.get("records"))},
        )

    run_async(lambda: run_in_session(work))


async def upsert_period_records(
    session,
    *,
    table_name: str,
    gstin: str,
    year: str,
    month: str,
    upstream_status_code: Any,
    records: list[Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    from .persistence_common import ensure_client

    client_id = await ensure_client(session, gstin)
    values = {
        "client_id": client_id,
        "year": year,
        "month": month,
        "upstream_status_code": upstream_status_code,
    }
    if records is not None:
        values["records"] = records
    if extra:
        values.update(extra)
    await upsert_row(session, table_name, values)


def base_period_args(args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[str, str, str]:
    return (
        sentinel(kwargs.get("gstin") or get_arg(args, 0)),
        sentinel(kwargs.get("year") or get_arg(args, 1)),
        sentinel(kwargs.get("month") or get_arg(args, 2)),
    )


def get_arg(args: tuple[Any, ...], index: int) -> Any:
    return args[index] if len(args) > index else None


GSTR1_PERSISTERS = {
    "get_gstr1_advance_tax": persist_gstr1_advance_tax,
    "get_gstr1_b2b": persist_gstr1_b2b,
    "get_gstr1_summary": persist_gstr1_summary,
    "get_gstr1_b2csa": persist_gstr1_b2csa,
    "get_gstr1_b2cs": persist_gstr1_b2cs,
    "get_gstr1_cdnr": persist_gstr1_cdnr,
    "get_gstr1_doc_issue": persist_gstr1_doc_issue,
    "get_gstr1_hsn": persist_gstr1_hsn,
    "get_gstr1_nil": persist_gstr1_nil,
    "get_gstr1_b2cl": persist_gstr1_b2cl,
    "get_gstr1_cdnur": persist_gstr1_cdnur,
    "get_gstr1_exp": persist_gstr1_exp,
    "get_gstr1_txp": persist_gstr1_txp,
}
