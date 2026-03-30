from typing import Optional
from services.ledger_service import *
from fastapi import APIRouter, Query

router = APIRouter(prefix="/ledgers", tags=["ledgers"])


@router.get("/ledgers/{gstin}/{year}/{month}/balance")
def cash_itc_balance(gstin: str, year: str, month: str):
    return get_cash_itc_balance(gstin, year, month)


@router.get("/ledgers/{gstin}/cash")
def cash_ledger(
    gstin: str,
    from_date: str = Query(..., alias="from"),
    to_date:   str = Query(..., alias="to"),
):
    return get_cash_ledger(gstin, from_date, to_date)


@router.get("/ledgers/{gstin}/itc")
def itc_ledger(
    gstin: str,
    from_date: str = Query(..., alias="from"),
    to_date:   str = Query(..., alias="to"),
):
    return get_itc_ledger(gstin, from_date, to_date)


@router.get("/ledgers/{gstin}/tax/{year}/{month}")
def return_liability_ledger(
    gstin:     str,
    year:      str,
    month:     str,
    from_date: str = Query(..., alias="from"),
    to_date:   str = Query(..., alias="to"),
):
    return get_return_liability_ledger(gstin, year, month, from_date, to_date)