from typing import Optional
from services.gstr_3B_service import *
from fastapi import APIRouter, Query

router = APIRouter(prefix="/gstr3B", tags=["gstr3B"])


@router.get("/gstr3b/{gstin}/{year}/{month}")
def gstr3b_details(gstin: str, year: str, month: str):
    return get_gstr3b_details(gstin, year, month)


@router.get("/gstr3b/{gstin}/{year}/{month}/auto-liability-calc")
def gstr3b_auto_liability(gstin: str, year: str, month: str):
    return get_gstr3b_auto_liability(gstin, year, month)