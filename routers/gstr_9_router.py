import requests
from typing import Dict, Any, Optional
import config
from session_storage import get_session
from services.gstr_9_service import *
from fastapi import APIRouter , HTTPException, Query

router = APIRouter(prefix="/gstr9", tags=["gstr9"])

@router.get("/gstr9/{gstin}/auto-calculated")
def gstr9_auto_calculated(
    gstin: str,
    financial_year: str,
):
    result = get_gstr9_auto_calculated(gstin, financial_year)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)

    return result

@router.get("/gstr9/{gstin}/table-8a")
def gstr9_table8a(
    gstin: str,
    financial_year: str,
    file_number: str,
):
    result = get_gstr9_table8a(gstin, financial_year, file_number)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)

    return result

@router.get("/gstr9/{gstin}")
def gstr9_details(
    gstin: str,
    financial_year: str,
):
    result = get_gstr9_details(gstin, financial_year)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)

    return result
