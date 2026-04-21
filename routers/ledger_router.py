import requests
from typing import Dict, Any, Optional
import config
from session_storage import get_session
from services.ledger_service import *
from fastapi import APIRouter , HTTPException, Query

router = APIRouter(prefix="/ledgers", tags=["ledgers"])




@router.get("/ledgers/{gstin}/{year}/{month}/balance")
def cash_itc_balance(gstin: str, year: str, month: str):
    result = get_cash_itc_balance(gstin, year, month)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.get("/ledgers/{gstin}/cash")
def cash_ledger(
    gstin: str,
    from_date: str = Query(..., alias="from"),
    to_date:   str = Query(..., alias="to"),
):
    result = get_cash_ledger(gstin, from_date, to_date)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.get("/ledgers/{gstin}/itc")
def itc_ledger(
    gstin: str,
    from_date: str = Query(..., alias="from"),
    to_date:   str = Query(..., alias="to"),
):
    result = get_itc_ledger(gstin, from_date, to_date)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)

    return result

@router.get("/ledgers/{gstin}/tax/{year}/{month}")
def return_liability_ledger(
    gstin:     str,
    year:      str,
    month:     str,
    from_date: str = Query(..., alias="from"),
    to_date:   str = Query(..., alias="to"),
):
    result = get_return_liability_ledger(gstin, year, month, from_date, to_date)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)

    return result