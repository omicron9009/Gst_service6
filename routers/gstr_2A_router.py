
from typing import Optional
from services.gstr_2A_service import *
from fastapi import APIRouter, Query

router = APIRouter(prefix="/gstr2A", tags=["gstr2A"])


@router.get("/b2b/{gstin}/{year}/{month}")
def gstr2a_b2b(gstin: str, year: str, month: str):
    return get_gstr2a_b2b(gstin, year, month)


@router.get("/b2ba/{gstin}/{year}/{month}")
def gstr2a_b2ba(gstin: str, year: str, month: str, counterparty_gstin: str = None):
    return get_gstr2a_b2ba(gstin, year, month, counterparty_gstin=counterparty_gstin)


@router.get("/cdn/{gstin}/{year}/{month}")
def gstr2a_cdn(gstin: str, year: str, month: str, counterparty_gstin: str = None, from_date: str = None):
    return get_gstr2a_cdn(gstin, year, month, counterparty_gstin=counterparty_gstin, from_date=from_date)


@router.get("/cdna/{gstin}/{year}/{month}")
def gstr2a_cdna(gstin: str, year: str, month: str, counterparty_gstin: str = None):
    return get_gstr2a_cdna(gstin, year, month, counterparty_gstin=counterparty_gstin)


@router.get("/document/{gstin}/{year}/{month}")
def gstr2a_document(gstin: str, year: str, month: str):
    return get_gstr2a_document(gstin, year, month)


@router.get("/isd/{gstin}/{year}/{month}")
def gstr2a_isd(gstin: str, year: str, month: str, counterparty_gstin: str = None):
    return get_gstr2a_isd(gstin, year, month, counterparty_gstin=counterparty_gstin)


@router.get("/gstr2a/{gstin}/{year}/{month}/tds")
def gstr2a_tds(gstin: str, year: str, month: str):
    return get_gstr2a_tds(gstin, year, month)