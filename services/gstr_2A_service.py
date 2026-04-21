
#--------------not available----------- 
#  amdhist 
#  ecom - 
#  ecoma -Must do 
#  impg - Must do 
#  impgsez 
#  tcs

 
# -------------------------------------

# functions available in gstr 2a 
#  b2b 
#  b2ba 
#  cdn 
#  cdna
#  2a doc
#  isd 
#  tds

import requests
from typing import Dict, Any, Optional
import config
from session_storage import get_session

# Persistence
from database.core.database import get_sync_db
from database.models.client import Client
from database.services.gstr2a.models import Gstr2AB2B


def _get_or_create_client(gstin: str, session) -> Client:
    client = session.query(Client).filter(Client.gstin == gstin).first()
    if not client:
        client = Client(gstin=gstin, username="", is_active=True)
        session.add(client)
        session.flush()
    return client


def get_gstr2a_b2b(gstin: str, year: str, month: str) -> Dict[str, Any]:
    """
    Fetch GSTR-2A B2B invoices data and return a readable structure.
    """
    session = get_session(gstin)
    if not session:
        return {
            "success": False,
            "message": "GST session not found. Verify OTP first.",
            "request": {"gstin": gstin, "year": year, "month": month}
        }

    token = session.get("access_token")
    url = f"{config.BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2a/b2b/{year}/{month}"
    headers = {
        "Authorization": token,
        "x-api-key": config.API_KEY,
        "x-api-version": config.API_VERSION,
        "x-source": "primary"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        payload = response.json()
    except Exception as e:
        return {
            "success": False,
            "message": "Failed to contact GST API",
            "error": str(e),
        }

    outer = payload.get("data", {})
    status_cd = str(outer.get("status_cd", ""))
    b2b_data = outer.get("data", {}).get("b2b", [])

    interpreted = []
    for entry in b2b_data:
        ctin = entry.get("ctin")
        cfs = entry.get("cfs")
        cfs3b = entry.get("cfs3b")
        filed_date = entry.get("fldtr1")
        filing_period = entry.get("flprdr1")

        for inv in entry.get("inv", []):
            total_taxable = 0.0
            total_igst = 0.0
            total_cgst = 0.0
            total_sgst = 0.0
            total_cess = 0.0

            items = []
            for item in inv.get("itms", []):
                det = item.get("itm_det", {})
                txval = det.get("txval") or 0.0
                igst = det.get("iamt") or 0.0
                cgst = det.get("camt") or 0.0
                sgst = det.get("samt") or 0.0
                cess = det.get("csamt") or 0.0

                total_taxable += txval
                total_igst += igst
                total_cgst += cgst
                total_sgst += sgst
                total_cess += cess

                items.append({
                    "item_number": item.get("num"),
                    "tax_rate": det.get("rt"),
                    "taxable_value": txval,
                    "igst": igst,
                    "cgst": cgst,
                    "sgst": sgst,
                    "cess": cess,
                })

            interpreted.append({
                "supplier_gstin": ctin,
                "filing_status_gstr1": cfs,
                "filing_status_gstr3b": cfs3b,
                "supplier_filed_date": filed_date,
                "supplier_filing_period": filing_period,
                "invoice_number": inv.get("inum"),
                "invoice_date": inv.get("idt"),
                "invoice_type": inv.get("inv_typ"),
                "invoice_value": inv.get("val"),
                "place_of_supply": inv.get("pos"),
                "reverse_charge": inv.get("rchrg"),
                "source_type": inv.get("srctyp"),
                "irn": inv.get("irn"),
                "irn_gen_date": inv.get("irngendate"),
                "taxable_value": total_taxable,
                "igst": total_igst,
                "cgst": total_cgst,
                "sgst": total_sgst,
                "cess": total_cess,
                "items": items,
            })

    result = {
        "success": True,
        "status_cd": status_cd,
        "request": {
            "gstin": gstin,
            "year": year,
            "month": month,
            "endpoint": "GSTR-2A B2B"
        },
        "upstream_status_code": response.status_code,
        "records": interpreted,
        "raw": payload
    }

    # Persist to DB
    try:
        db_session = get_sync_db()
        try:
            client = _get_or_create_client(gstin, db_session)

            existing = db_session.query(Gstr2AB2B).filter(
                Gstr2AB2B.client_id == client.id,
                Gstr2AB2B.year == year,
                Gstr2AB2B.month == month,
            ).first()

            if existing:
                existing.records = interpreted
                existing.upstream_status_code = response.status_code
                existing.status_cd = status_cd
            else:
                record = Gstr2AB2B(
                    client_id=client.id,
                    year=year,
                    month=month,
                    records=interpreted,
                    upstream_status_code=response.status_code,
                    status_cd=status_cd,
                )
                db_session.add(record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving GSTR2A B2B: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session for GSTR2A B2B: {e}")

    return result

def get_gstr2a_b2ba(gstin: str, year: str, month: str, counterparty_gstin: str = None) -> Dict[str, Any]:
    """
    Fetch GSTR-2A B2BA (Amended B2B invoices) data and return a readable structure.
    """
    session = get_session(gstin)
    if not session:
        return {
            "success": False,
            "message": "GST session not found. Verify OTP first.",
            "request": {"gstin": gstin, "year": year, "month": month}
        }

    token = session.get("access_token")
    url = f"{config.BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2a/b2ba/{year}/{month}"
    headers = {
        "Authorization": token,
        "x-api-key": config.API_KEY,
        "x-api-version": config.API_VERSION,
        "x-source": "primary"
    }

    params = {}
    if counterparty_gstin:
        params["counterparty_gstin"] = counterparty_gstin

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        payload = response.json()
    except Exception as e:
        return {
            "success": False,
            "message": "Failed to contact GST API",
            "error": str(e),
        }

    b2ba_data = (
        payload.get("data", {})
               .get("data", {})
               .get("b2ba", [])
    )

    AMENDMENT_TYPE_LABELS = {
        "D": "Amended",
        "N": "New",
    }

    interpreted = []
    for entry in b2ba_data:
        ctin         = entry.get("ctin")
        cfs          = entry.get("cfs")
        cfs3b        = entry.get("cfs3b")
        filed_date   = entry.get("fldtr1")
        filing_period = entry.get("flprdr1")

        for inv in entry.get("inv", []):
            items = []
            for item in inv.get("itms", []):
                det = item.get("itm_det", {})
                items.append({
                    "item_number": item.get("num"),
                    "tax_rate": det.get("rt"),
                    "taxable_value": det.get("txval"),
                    "igst": det.get("iamt"),
                    "cgst": det.get("camt"),
                    "sgst": det.get("samt"),
                    "cess": det.get("csamt"),
                })

            atyp = inv.get("atyp")
            interpreted.append({
                "supplier_gstin": ctin,
                "filing_status_gstr1": cfs,
                "filing_status_gstr3b": cfs3b,
                "supplier_filed_date": filed_date,
                "supplier_filing_period": filing_period,
                "invoice_number": inv.get("inum"),
                "invoice_date": inv.get("idt"),
                "original_invoice_number": inv.get("oinum"),
                "original_invoice_date": inv.get("oidt"),
                "amendment_period": inv.get("aspd"),
                "amendment_type_code": atyp,
                "amendment_type": AMENDMENT_TYPE_LABELS.get(atyp, atyp),
                "invoice_type": inv.get("inv_typ"),
                "invoice_value": inv.get("val"),
                "place_of_supply": inv.get("pos"),
                "reverse_charge": inv.get("rchrg"),
                "items": items,
            })

    return {
        "success": True,
        "request": {
            "gstin": gstin,
            "year": year,
            "month": month,
            "counterparty_gstin": counterparty_gstin,
            "endpoint": "GSTR-2A B2BA"
        },
        "upstream_status_code": response.status_code,
        "records": interpreted,
        "raw": payload
    }

def get_gstr2a_cdn(gstin: str, year: str, month: str, counterparty_gstin: str = None, from_date: str = None) -> Dict[str, Any]:
    """
    Fetch GSTR-2A CDN (Credit/Debit Notes) data and return a readable structure.
    """
    session = get_session(gstin)
    if not session:
        return {
            "success": False,
            "message": "GST session not found. Verify OTP first.",
            "request": {"gstin": gstin, "year": year, "month": month}
        }

    token = session.get("access_token")
    url = f"{config.BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2a/cdn/{year}/{month}"
    headers = {
        "Authorization": token,
        "x-api-key": config.API_KEY,
        "x-api-version": config.API_VERSION,
        "x-source": "primary"
    }

    params = {}
    if counterparty_gstin:
        params["counterparty_gstin"] = counterparty_gstin
    if from_date:
        params["from"] = from_date

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        payload = response.json()
    except Exception as e:
        return {
            "success": False,
            "message": "Failed to contact GST API",
            "error": str(e),
        }

    cdn_data = (
        payload.get("data", {})
               .get("data", {})
               .get("cdn", [])
    )

    NOTE_TYPE_LABELS = {
        "C": "Credit Note",
        "D": "Debit Note",
    }

    interpreted = []
    for entry in cdn_data:
        ctin          = entry.get("ctin")
        cfs           = entry.get("cfs")
        cfs3b         = entry.get("cfs3b")
        filed_date    = entry.get("fldtr1")
        filing_period = entry.get("flprdr1")

        for note in entry.get("nt", []):
            items = []
            for item in note.get("itms", []):
                det = item.get("itm_det", {})
                items.append({
                    "item_number": item.get("num"),
                    "tax_rate": det.get("rt"),
                    "taxable_value": det.get("txval"),
                    "igst": det.get("iamt"),
                    "cgst": det.get("camt"),
                    "sgst": det.get("samt"),
                    "cess": det.get("csamt"),
                })

            ntty = note.get("ntty")
            interpreted.append({
                "supplier_gstin": ctin,
                "filing_status_gstr1": cfs,
                "filing_status_gstr3b": cfs3b,
                "supplier_filed_date": filed_date,
                "supplier_filing_period": filing_period,
                "note_number": note.get("nt_num"),
                "note_date": note.get("nt_dt"),
                "note_type_code": ntty,
                "note_type": NOTE_TYPE_LABELS.get(ntty, ntty),
                "invoice_type": note.get("inv_typ"),
                "note_value": note.get("val"),
                "place_of_supply": note.get("pos"),
                "reverse_charge": note.get("rchrg"),
                "delete_flag": note.get("d_flag"),
                "source_type": note.get("srctyp"),
                "irn": note.get("irn"),
                "irn_gen_date": note.get("irngendate"),
                "items": items,
            })

    return {
        "success": True,
        "request": {
            "gstin": gstin,
            "year": year,
            "month": month,
            "counterparty_gstin": counterparty_gstin,
            "from_date": from_date,
            "endpoint": "GSTR-2A CDN"
        },
        "upstream_status_code": response.status_code,
        "records": interpreted,
        "raw": payload
    }

def get_gstr2a_cdna(gstin: str, year: str, month: str, counterparty_gstin: str = None) -> Dict[str, Any]:
    """
    Fetch GSTR-2A CDNA (Amended Credit/Debit Notes) data and return a readable structure.
    """
    session = get_session(gstin)
    if not session:
        return {
            "success": False,
            "message": "GST session not found. Verify OTP first.",
            "request": {"gstin": gstin, "year": year, "month": month}
        }

    token = session.get("access_token")
    url = f"{config.BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2a/cdna/{year}/{month}"
    headers = {
        "Authorization": token,
        "x-api-key": config.API_KEY,
        "x-api-version": config.API_VERSION,
        "x-source": "primary"
    }

    params = {}
    if counterparty_gstin:
        params["counterparty_gstin"] = counterparty_gstin

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        payload = response.json()
    except Exception as e:
        return {
            "success": False,
            "message": "Failed to contact GST API",
            "error": str(e),
        }

    cdna_data = (
        payload.get("data", {})
               .get("data", {})
               .get("cdna", [])
    )

    NOTE_TYPE_LABELS = {
        "C": "Credit Note",
        "D": "Debit Note",
    }

    interpreted = []
    for entry in cdna_data:
        ctin = entry.get("ctin")
        cfs  = entry.get("cfs")

        for note in entry.get("nt", []):
            items = []
            for item in note.get("itms", []):
                det = item.get("itm_det", {})
                items.append({
                    "item_number": item.get("num"),
                    "tax_rate": det.get("rt"),
                    "taxable_value": det.get("txval"),
                    "igst": det.get("iamt"),
                    "cgst": det.get("camt"),
                    "sgst": det.get("samt"),
                    "cess": det.get("csamt"),
                })

            ntty = note.get("ntty")
            interpreted.append({
                "supplier_gstin": ctin,
                "filing_status_gstr1": cfs,
                "note_number": note.get("nt_num"),
                "note_date": note.get("nt_dt"),
                "original_note_number": note.get("ont_num"),
                "original_note_date": note.get("ont_dt"),
                "note_type_code": ntty,
                "note_type": NOTE_TYPE_LABELS.get(ntty, ntty),
                "invoice_number": note.get("inum"),
                "invoice_date": note.get("idt"),
                "invoice_type": note.get("inv_typ"),
                "note_value": note.get("val"),
                "place_of_supply": note.get("pos"),
                "reverse_charge": note.get("rchrg"),
                "delete_flag": note.get("d_flag"),
                "diff_percent": note.get("diff_percent"),
                "pre_gst": note.get("p_gst"),
                "items": items,
            })

    return {
        "success": True,
        "request": {
            "gstin": gstin,
            "year": year,
            "month": month,
            "counterparty_gstin": counterparty_gstin,
            "endpoint": "GSTR-2A CDNA"
        },
        "upstream_status_code": response.status_code,
        "records": interpreted,
        "raw": payload
    }


def get_gstr2a_document(gstin: str, year: str, month: str) -> Dict[str, Any]:
    """
    Fetch complete GSTR-2A document (b2b, b2ba, cdn sections) and return a readable structure.
    """
    session = get_session(gstin)
    if not session:
        return {
            "success": False,
            "message": "GST session not found. Verify OTP first.",
            "request": {"gstin": gstin, "year": year, "month": month}
        }

    token = session.get("access_token")
    url = f"{config.BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2a/{year}/{month}"
    headers = {
        "Authorization": token,
        "x-api-key": config.API_KEY,
        "x-api-version": config.API_VERSION,
        "x-source": "primary"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        payload = response.json()
    except Exception as e:
        return {
            "success": False,
            "message": "Failed to contact GST API",
            "error": str(e),
        }

    doc_data = payload.get("data", {}).get("data", {})

    # ── helpers ──────────────────────────────────────────────────────────────

    NOTE_TYPE_LABELS = {"C": "Credit Note", "D": "Debit Note"}
    AMENDMENT_TYPE_LABELS = {"D": "Amended", "N": "New"}

    def parse_items(itms: list) -> list:
        items = []
        for item in itms:
            det = item.get("itm_det", {})
            items.append({
                "item_number": item.get("num"),
                "tax_rate":    det.get("rt"),
                "taxable_value": det.get("txval"),
                "igst":  det.get("iamt"),
                "cgst":  det.get("camt"),
                "sgst":  det.get("samt"),
                "cess":  det.get("csamt"),
            })
        return items

    def parse_b2b(b2b_data: list) -> list:
        records = []
        for entry in b2b_data:
            ctin          = entry.get("ctin")
            cfs           = entry.get("cfs")
            cfs3b         = entry.get("cfs3b")
            filed_date    = entry.get("fldtr1")
            filing_period = entry.get("flprdr1")
            for inv in entry.get("inv", []):
                records.append({
                    "supplier_gstin":       ctin,
                    "filing_status_gstr1":  cfs,
                    "filing_status_gstr3b": cfs3b,
                    "supplier_filed_date":  filed_date,
                    "supplier_filing_period": filing_period,
                    "invoice_number": inv.get("inum"),
                    "invoice_date":   inv.get("idt"),
                    "invoice_type":   inv.get("inv_typ"),
                    "invoice_value":  inv.get("val"),
                    "place_of_supply": inv.get("pos"),
                    "reverse_charge":  inv.get("rchrg"),
                    "source_type":     inv.get("srctyp"),
                    "irn":             inv.get("irn"),
                    "irn_gen_date":    inv.get("irngendate"),
                    "items": parse_items(inv.get("itms", [])),
                })
        return records

    def parse_b2ba(b2ba_data: list) -> list:
        records = []
        for entry in b2ba_data:
            ctin          = entry.get("ctin")
            cfs           = entry.get("cfs")
            cfs3b         = entry.get("cfs3b")
            filed_date    = entry.get("fldtr1")
            filing_period = entry.get("flprdr1")
            for inv in entry.get("inv", []):
                atyp = inv.get("atyp")
                records.append({
                    "supplier_gstin":         ctin,
                    "filing_status_gstr1":    cfs,
                    "filing_status_gstr3b":   cfs3b,
                    "supplier_filed_date":    filed_date,
                    "supplier_filing_period": filing_period,
                    "invoice_number":          inv.get("inum"),
                    "invoice_date":            inv.get("idt"),
                    "original_invoice_number": inv.get("oinum"),
                    "original_invoice_date":   inv.get("oidt"),
                    "amendment_period":        inv.get("aspd"),
                    "amendment_type_code":     atyp,
                    "amendment_type":          AMENDMENT_TYPE_LABELS.get(atyp, atyp),
                    "invoice_type":            inv.get("inv_typ"),
                    "invoice_value":           inv.get("val"),
                    "place_of_supply":         inv.get("pos"),
                    "reverse_charge":          inv.get("rchrg"),
                    "items": parse_items(inv.get("itms", [])),
                })
        return records

    def parse_cdn(cdn_data: list) -> list:
        records = []
        for entry in cdn_data:
            ctin          = entry.get("ctin")
            cfs           = entry.get("cfs")
            cfs3b         = entry.get("cfs3b")
            filed_date    = entry.get("fldtr1")
            filing_period = entry.get("flprdr1")
            for note in entry.get("nt", []):
                ntty = note.get("ntty")
                records.append({
                    "supplier_gstin":         ctin,
                    "filing_status_gstr1":    cfs,
                    "filing_status_gstr3b":   cfs3b,
                    "supplier_filed_date":    filed_date,
                    "supplier_filing_period": filing_period,
                    "note_number":    note.get("nt_num"),
                    "note_date":      note.get("nt_dt"),
                    "note_type_code": ntty,
                    "note_type":      NOTE_TYPE_LABELS.get(ntty, ntty),
                    "invoice_type":   note.get("inv_typ"),
                    "note_value":     note.get("val"),
                    "place_of_supply": note.get("pos"),
                    "reverse_charge":  note.get("rchrg"),
                    "delete_flag":     note.get("d_flag"),
                    "source_type":     note.get("srctyp"),
                    "irn":             note.get("irn"),
                    "irn_gen_date":    note.get("irngendate"),
                    "items": parse_items(note.get("itms", [])),
                })
        return records

    # ── assemble ─────────────────────────────────────────────────────────────

    return {
        "success": True,
        "request": {
            "gstin": gstin,
            "year": year,
            "month": month,
            "endpoint": "GSTR-2A Document"
        },
        "upstream_status_code": response.status_code,
        "filing_period": doc_data.get("fp"),
        "taxpayer_gstin": doc_data.get("gstin"),
        "b2b":  parse_b2b(doc_data.get("b2b", [])),
        "b2ba": parse_b2ba(doc_data.get("b2ba", [])),
        "cdn":  parse_cdn(doc_data.get("cdn", [])),
        "raw": payload
    }

def get_gstr2a_isd(gstin: str, year: str, month: str, counterparty_gstin: str = None) -> Dict[str, Any]:
    """
    Fetch GSTR-2A ISD (Input Service Distributor) data and return a readable structure.
    """
    session = get_session(gstin)
    if not session:
        return {
            "success": False,
            "message": "GST session not found. Verify OTP first.",
            "request": {"gstin": gstin, "year": year, "month": month}
        }

    token = session.get("access_token")
    url = f"{config.BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2a/isd/{year}/{month}"
    headers = {
        "Authorization": token,
        "x-api-key": config.API_KEY,
        "x-api-version": config.API_VERSION,
        "x-source": "primary"
    }

    params = {}
    if counterparty_gstin:
        params["counterparty_gstin"] = counterparty_gstin

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        payload = response.json()
    except Exception as e:
        return {
            "success": False,
            "message": "Failed to contact GST API",
            "error": str(e),
        }

    # note: isd sits directly under data{}, not data.data{}
    isd_data = payload.get("data", {}).get("isd", [])

    ISD_DOC_TYPE_LABELS = {
        "ISD":  "ISD Invoice",
        "ISDCN": "ISD Credit Note",
        "ISDN":  "ISD Debit Note",
    }

    interpreted = []
    for entry in isd_data:
        ctin = entry.get("ctin")
        cfs  = entry.get("cfs")

        for doc in entry.get("doclist", []):
            isd_docty = doc.get("isd_docty")
            interpreted.append({
                "distributor_gstin":    ctin,
                "filing_status_gstr1":  cfs,
                "document_number":      doc.get("docnum"),
                "document_date":        doc.get("docdt"),
                "document_type_code":   isd_docty,
                "document_type":        ISD_DOC_TYPE_LABELS.get(isd_docty, isd_docty),
                "itc_eligible":         doc.get("itc_elg"),
                "igst":  doc.get("iamt"),
                "cgst":  doc.get("camt"),
                "sgst":  doc.get("samt"),
                "cess":  doc.get("cess"),
            })

    return {
        "success": True,
        "request": {
            "gstin": gstin,
            "year": year,
            "month": month,
            "counterparty_gstin": counterparty_gstin,
            "endpoint": "GSTR-2A ISD"
        },
        "upstream_status_code": response.status_code,
        "records": interpreted,
        "raw": payload
    }


def get_gstr2a_tds(gstin: str, year: str, month: str) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{config.BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2a/tds/{year}/{month}"

    headers = {
        "Authorization": token,
        "x-api-key":     config.API_KEY,
        "x-api-version": config.API_VERSION,
        "x-source":      "primary",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        payload = response.json()
    except Exception as e:
        return {"success": False, "message": "Failed to contact GST API", "error": str(e)}

    outer_data = payload.get("data", {})
    status_cd  = str(outer_data.get("status_cd", ""))

    if status_cd == "0":
        error_block = outer_data.get("error", {})
        return {
            "success":    False,
            "status_cd":  "0",
            "error_code": error_block.get("error_cd"),
            "message":    error_block.get("message"),
            "raw":        payload,
        }

    inner = outer_data.get("data", {})

    # ── tds: TDS credit entries auto-populated from deductors' GSTR-7 ─────────
    # Each entry is one deductor's TDS deduction for the period.
    #
    # gstin_ded:       recipient GSTIN (the taxpayer whose ITC is being credited)
    # gstin_deductor:  deductor's GSTIN (the entity that deducted TDS)
    # deductor_name:   deductor's registered trade/legal name
    # month:           return period in MMYYYY format (e.g. "062025" = June 2025)
    # amt_ded:         base contract/invoice value on which TDS was deducted
    # iamt:            IGST TDS amount credited
    # camt:            CGST TDS amount credited
    # samt:            SGST TDS amount credited
    # (no cess on TDS)

    def _parse_tds_entry(entry: dict) -> Dict[str, Any]:
        igst = entry.get("iamt", 0) or 0.0
        cgst = entry.get("camt", 0) or 0.0
        sgst = entry.get("samt", 0) or 0.0
        total_tds = igst + cgst + sgst

        return {
            "deductor_name":    entry.get("deductor_name"),
            "deductor_gstin":   entry.get("gstin_deductor"),
            "recipient_gstin":  entry.get("gstin_ded"),
            "return_period":    entry.get("month"),        # "MMYYYY"

            # Base amount on which TDS was deducted
            "deduction_base_amount": entry.get("amt_ded", 0) or 0.0,

            # TDS tax credit breakdown
            "tds_credit": {
                "igst":      igst,
                "cgst":      cgst,
                "sgst":      sgst,
                "total":     total_tds,
            },
        }

    tds_entries = [_parse_tds_entry(e) for e in (inner.get("tds") or [])]

    # Grand totals across all deductors
    grand_base  = sum(e["deduction_base_amount"]  for e in tds_entries)
    grand_igst  = sum(e["tds_credit"]["igst"]      for e in tds_entries)
    grand_cgst  = sum(e["tds_credit"]["cgst"]      for e in tds_entries)
    grand_sgst  = sum(e["tds_credit"]["sgst"]      for e in tds_entries)

    return {
        "success":       True,
        "status_cd":     status_cd,

        # TDS credit entries — one per deductor per period
        "tds":           tds_entries,
        "entry_count":   len(tds_entries),

        # Aggregate TDS credit available across all deductors
        "grand_totals": {
            "deduction_base_amount": grand_base,
            "igst":                  grand_igst,
            "cgst":                  grand_cgst,
            "sgst":                  grand_sgst,
            "total_tds_credit":      grand_igst + grand_cgst + grand_sgst,
        },

        "raw": payload,
    }