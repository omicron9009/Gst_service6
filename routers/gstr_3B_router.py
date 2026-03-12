import requests
from typing import Dict, Any, Optional
from config import BASE_URL, API_KEY, API_VERSION
from session_storage import get_session
from services.gstr_3B_service import *
from fastapi import APIRouter , HTTPException, Query

router = APIRouter(prefix="/gstr3B", tags=["gstr3B"])

@router.get("/gstr3b/{gstin}/{year}/{month}")
def gstr3b_details(gstin: str, year: str, month: str):
    result = get_gstr3b_details(gstin, year, month)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.get("/gstr3b/{gstin}/{year}/{month}/auto-liability-calc")
def gstr3b_auto_liability(gstin: str, year: str, month: str):
    result = get_gstr3b_auto_liability(gstin, year, month)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)

    return result