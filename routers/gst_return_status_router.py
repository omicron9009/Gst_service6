
import requests
from typing import Dict, Any, Optional
import config
from session_storage import get_session
from services.gst_return_status_service import *
from fastapi import APIRouter , HTTPException, Query

router = APIRouter(prefix="/return_status", tags=["returnStatus"])


@router.get("/returns/{gstin}/{year}/{month}/status")
def gst_return_status(
    gstin:        str,
    year:         str,
    month:        str,
    reference_id: str = Query(..., description="Reference ID returned after save/reset"),
):
    result = get_gst_return_status(gstin, year, month, reference_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result)

    return result
