
from typing import Optional
from services.gst_return_status_service import *
from fastapi import APIRouter, Query

router = APIRouter(prefix="/return_status", tags=["returnStatus"])


@router.get("/returns/{gstin}/{year}/{month}/status")
def gst_return_status(
    gstin:        str,
    year:         str,
    month:        str,
    reference_id: str = Query(..., description="Reference ID returned after save/reset"),
):
    return get_gst_return_status(gstin, year, month, reference_id)
