# routers/gst_r1_router.py

from typing import Optional
from fastapi import APIRouter, Query

# BUG FIX 1: Removed import of get_gstr1_ata — the function is commented out in
#             gstr1_service.py and does not exist; importing it caused an ImportError
#             at startup.
# BUG FIX 2: Gstr1AdvanceTaxResponse lives in gstr1.py (the schema module),
#             not in gstr1_service. Import it from there.
from schemas.gstr1 import Gstr1AdvanceTaxResponse
from services.gstr1_service import *

router = APIRouter(prefix="/gstr1", tags=["gstr1"])


@router.get(
    "/advance-tax/{gstin}/{year}/{month}",
    response_model=Gstr1AdvanceTaxResponse,
)
def gstr1_advance_tax(gstin: str, year: str, month: str):
    return get_gstr1_advance_tax(gstin, year, month)


@router.get("/b2b/{gstin}/{year}/{month}")
def gstr1_b2b(
    gstin: str,
    year: str,
    month: str,
    action_required: str | None = None,
    from_date: str | None = None,
    counterparty_gstin: str | None = None,
):
    return get_gstr1_b2b(
        gstin,
        year,
        month,
        action_required,
        from_date,
        counterparty_gstin,
    )


@router.get("/summary/{gstin}/{year}/{month}")
def fetch_gstr1_summary(gstin: str, year: str, month: str, summary_type: str = Query("short", enum=["short", "long"])):
    """
    Fetch GSTR1 summary (short or long).

    Examples:
        /gstr1/summary/{gstin}/2023/12
        /gstr1/summary/{gstin}/2023/12?summary_type=long
    """
    return get_gstr1_summary(
        gstin=gstin,
        year=year,
        month=month,
        summary_type=summary_type,
    )


@router.get("/b2csa/{gstin}/{year}/{month}")
def gstr1_b2csa(gstin: str, year: str, month: str):
    return get_gstr1_b2csa(gstin, year, month)


@router.get("/b2cs/{gstin}/{year}/{month}")
def gstr1_b2cs(gstin: str, year: str, month: str):
    return get_gstr1_b2cs(gstin, year, month)


from services.gstr1_service import get_gstr1_cdnr

@router.get("/cdnr/{gstin}/{year}/{month}")
def gstr1_cdnr(
    gstin: str,
    year: str,
    month: str,
    action_required: Optional[str] = Query(None, description="Y or N"),
    from_date: Optional[str] = Query(None, alias="from", description="DD/MM/YYYY"),
):
    return get_gstr1_cdnr(
        gstin=gstin,
        year=year,
        month=month,
        action_required=action_required,
        from_date=from_date,
    )


@router.get("/doc-issue/{gstin}/{year}/{month}")
def gstr1_doc_issue(gstin: str, year: str, month: str):
    return get_gstr1_doc_issue(gstin, year, month)


@router.get("/hsn/{gstin}/{year}/{month}")
def gstr1_hsn(gstin: str, year: str, month: str):
    return get_gstr1_hsn(gstin, year, month)


@router.get("/nil/{gstin}/{year}/{month}")
def gstr1_nil(gstin: str, year: str, month: str):
    return get_gstr1_nil(gstin, year, month)


@router.get("/b2cl/{gstin}/{year}/{month}")
def gstr1_b2cl(gstin: str, year: str, month: str, state_code: str = None):
    return get_gstr1_b2cl(gstin, year, month, state_code=state_code)


@router.get("/cdnur/{gstin}/{year}/{month}")
def gstr1_cdnur(gstin: str, year: str, month: str):
    return get_gstr1_cdnur(gstin, year, month)


@router.get("/exp/{gstin}/{year}/{month}")
def gstr1_exp(gstin: str, year: str, month: str):
    return get_gstr1_exp(gstin, year, month)


@router.get("/gstr1/{gstin}/{year}/{month}/txp")
def gstr1_txp(
    gstin: str,
    year:  str,
    month: str,
    counterparty_gstin: Optional[str] = Query(None, description="Filter by counterparty GSTIN"),
    action_required:    Optional[str] = Query(None, description="Y = action needed, N = already accepted/uploaded"),
    from_date:          Optional[str] = Query(None, alias="from", description="From date DD/MM/YYYY"),
):
    return get_gstr1_txp(gstin, year, month, counterparty_gstin, action_required, from_date)