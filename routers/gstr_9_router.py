from typing import Optional
from services.gstr_9_service import *
from fastapi import APIRouter, Query

router = APIRouter(prefix="/gstr9", tags=["gstr9"])


@router.get("/gstr9/{gstin}/auto-calculated")
def gstr9_auto_calculated(
    gstin: str,
    financial_year: str,
):
    return get_gstr9_auto_calculated(gstin, financial_year)


@router.get("/gstr9/{gstin}/table-8a")
def gstr9_table8a(
    gstin: str,
    financial_year: str,
    file_number: str,
):
    return get_gstr9_table8a(gstin, financial_year, file_number)


@router.get("/gstr9/{gstin}")
def gstr9_details(
    gstin: str,
    financial_year: str,
):
    return get_gstr9_details(gstin, financial_year)
