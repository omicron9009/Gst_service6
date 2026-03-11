
#--------------not available----------- 
#  amdhist 
#  ecom 
#  ecoma 
#  impg 
#  impgsez 
#  tcs
#  tds
#  
# -------------------------------------




import requests
from typing import Dict, Any, Optional
from config import BASE_URL, API_KEY, API_VERSION
from session_storage import get_session


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
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2a/b2b/{year}/{month}"
    headers = {
        "Authorization": token,
        "x-api-key": API_KEY,
        "x-api-version": API_VERSION,
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

    b2b_data = (
        payload.get("data", {})
               .get("data", {})
               .get("b2b", [])
    )

    interpreted = []
    for entry in b2b_data:
        ctin = entry.get("ctin")
        cfs = entry.get("cfs")
        cfs3b = entry.get("cfs3b")
        filed_date = entry.get("fldtr1")
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
                "items": items,
            })

    return {
        "success": True,
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
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2a/b2ba/{year}/{month}"
    headers = {
        "Authorization": token,
        "x-api-key": API_KEY,
        "x-api-version": API_VERSION,
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
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2a/cdn/{year}/{month}"
    headers = {
        "Authorization": token,
        "x-api-key": API_KEY,
        "x-api-version": API_VERSION,
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
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2a/cdna/{year}/{month}"
    headers = {
        "Authorization": token,
        "x-api-key": API_KEY,
        "x-api-version": API_VERSION,
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
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2a/{year}/{month}"
    headers = {
        "Authorization": token,
        "x-api-key": API_KEY,
        "x-api-version": API_VERSION,
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
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2a/isd/{year}/{month}"
    headers = {
        "Authorization": token,
        "x-api-key": API_KEY,
        "x-api-version": API_VERSION,
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