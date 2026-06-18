
import requests
from typing import Dict, Any, Optional
import config
from session_storage import get_session
from services.gstr_2A_service import *
from fastapi import APIRouter , HTTPException, Query

router = APIRouter(prefix="/gstr2A", tags=["gstr2A"])


@router.get("/b2b/{gstin}/{year}/{month}")
def gstr2a_b2b(gstin: str, year: str, month: str):
    result = get_gstr2a_b2b(gstin, year, month)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result

@router.get("/b2ba/{gstin}/{year}/{month}")
def gstr2a_b2ba(gstin: str, year: str, month: str, counterparty_gstin: str = None):
    result = get_gstr2a_b2ba(gstin, year, month, counterparty_gstin=counterparty_gstin)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result

@router.get("/cdn/{gstin}/{year}/{month}")
def gstr2a_cdn(gstin: str, year: str, month: str, counterparty_gstin: str = None, from_date: str = None):
    result = get_gstr2a_cdn(gstin, year, month, counterparty_gstin=counterparty_gstin, from_date=from_date)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result

@router.get("/cdna/{gstin}/{year}/{month}")
def gstr2a_cdna(gstin: str, year: str, month: str, counterparty_gstin: str = None):
    result = get_gstr2a_cdna(gstin, year, month, counterparty_gstin=counterparty_gstin)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result

@router.get("/document/{gstin}/{year}/{month}")
def gstr2a_document(gstin: str, year: str, month: str):
    result = get_gstr2a_document(gstin, year, month)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result

@router.get("/isd/{gstin}/{year}/{month}")
def gstr2a_isd(gstin: str, year: str, month: str, counterparty_gstin: str = None):
    result = get_gstr2a_isd(gstin, year, month, counterparty_gstin=counterparty_gstin)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)
    return result

@router.get("/gstr2a/{gstin}/{year}/{month}/tds")
def gstr2a_tds(gstin: str, year: str, month: str):
    result = get_gstr2a_tds(gstin, year, month)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)

    return result