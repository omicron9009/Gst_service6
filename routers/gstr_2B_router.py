import requests
from typing import Dict, Any, Optional
import config
from session_storage import get_session
from services.gstr_2B_service import *
from fastapi import APIRouter , HTTPException, Query

router = APIRouter(prefix="/gstr2B", tags=["gstr2B"])


@router.get("/gstr2b/{gstin}/{year}/{month}")
def gstr2b(
    gstin: str,
    year: str,
    month: str,
    file_number: int | None = None,
):
    """
    Fetch GSTR-2B for the given GSTIN and return period.

    Query params:
      - file_number (int, optional): Required when status_cd=3 is returned.
        Call once without it to get file_count, then call again with
        file_number=1 through file_count to retrieve all invoice pages.
    """
    result = get_gstr2b(gstin, year, month, file_number)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)

    return result


@router.get("/gstr2b/{gstin}/regenerate/status")
def gstr2b_regeneration_status(
    gstin: str,
    reference_id: str,
):
    result = get_gstr2b_regeneration_status(gstin, reference_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)

    return result