# not available 
# 
# 
# 
# 
# 
# 
# 
# available


import requests
from typing import Dict, Any, Optional
from config import BASE_URL, API_KEY, API_VERSION
from session_storage import get_session



def _parse_invoice_items(items: list) -> tuple[float, float, float, float, float, Optional[float]]:
    """Sum up tax components across line items. Returns (taxable, cgst, sgst, igst, cess, rate)."""
    taxable = cgst = sgst = igst = cess = 0.0
    rate = None
    for item in items:
        taxable += item.get("txval", 0) or 0
        cgst    += item.get("cgst",  0) or 0
        sgst    += item.get("sgst",  0) or 0
        igst    += item.get("igst",  0) or 0
        cess    += item.get("cess",  0) or 0
        rate     = item.get("rt", rate)
    return taxable, cgst, sgst, igst, cess, rate


def _parse_b2b_section(b2b_raw: list) -> tuple[list, Dict[str, float]]:
    """
    Parse b2b / b2ba supplier→invoice blocks.
    Works for both the old format (flat tax fields on inv) and
    the new (Oct 2024+) format (items array on inv).
    """
    invoices: list = []
    totals = dict(taxable=0.0, cgst=0.0, sgst=0.0, igst=0.0, cess=0.0, invoice_value=0.0)

    for supplier in b2b_raw:
        ctin    = supplier.get("ctin")
        trdnm   = supplier.get("trdnm")
        supprd  = supplier.get("supprd")
        supfildt = supplier.get("supfildt")

        for inv in supplier.get("inv", []):
            invoice_number = inv.get("inum")
            invoice_date   = inv.get("dt")
            invoice_value  = inv.get("val", 0.0) or 0.0
            pos            = inv.get("pos")
            reverse_charge = inv.get("rev")
            inv_type       = inv.get("typ")
            itc_available  = inv.get("itcavl")
            diff_percent   = inv.get("diffprcnt")
            irn            = inv.get("irn")
            irn_gen_date   = inv.get("irngendate")
            source_type    = inv.get("srctyp")
            ims_status     = inv.get("imsStatus")
            reason         = inv.get("rsn")

            # B2BA-specific: original invoice reference
            orig_inv_num   = inv.get("oinum")
            orig_inv_date  = inv.get("oidt")

            items_raw = inv.get("items", [])
            if items_raw:
                # New format (post Oct 2024) — items array
                taxable, cgst, sgst, igst, cess, rate = _parse_invoice_items(items_raw)
            else:
                # Old flat format — tax fields directly on inv dict
                taxable = inv.get("txval", 0) or 0.0
                cgst    = inv.get("cgst",  0) or 0.0
                sgst    = inv.get("sgst",  0) or 0.0
                igst    = inv.get("igst",  0) or 0.0
                cess    = inv.get("cess",  0) or 0.0
                rate    = None

            record: Dict[str, Any] = {
                "supplier_gstin":    ctin,
                "supplier_name":     trdnm,
                "supplier_period":   supprd,
                "supplier_file_date": supfildt,
                "invoice_number":    invoice_number,
                "invoice_date":      invoice_date,
                "invoice_value":     invoice_value,
                "place_of_supply":   pos,
                "invoice_type":      inv_type,
                "reverse_charge":    reverse_charge,
                "itc_available":     itc_available,
                "diff_percent":      diff_percent,
                "taxable_value":     taxable,
                "tax_rate":          rate,
                "cgst":              cgst,
                "sgst":              sgst,
                "igst":              igst,
                "cess":              cess,
                "irn":               irn,
                "irn_gen_date":      irn_gen_date,
                "source_type":       source_type,
                "ims_status":        ims_status,
                "reason":            reason,
            }
            if orig_inv_num:
                record["original_invoice_number"] = orig_inv_num
                record["original_invoice_date"]   = orig_inv_date

            invoices.append(record)

            totals["taxable"]       += taxable
            totals["cgst"]          += cgst
            totals["sgst"]          += sgst
            totals["igst"]          += igst
            totals["cess"]          += cess
            totals["invoice_value"] += invoice_value

    return invoices, totals


def _parse_cdnr_section(cdnr_raw: list) -> tuple[list, Dict[str, float]]:
    """
    Parse cdnr / cdnra (credit-debit note) supplier→note blocks.
    Same dual-format handling as b2b.
    """
    notes: list = []
    totals = dict(taxable=0.0, cgst=0.0, sgst=0.0, igst=0.0, cess=0.0, note_value=0.0)

    for supplier in cdnr_raw:
        ctin     = supplier.get("ctin")
        trdnm    = supplier.get("trdnm")
        supprd   = supplier.get("supprd")
        supfildt = supplier.get("supfildt")

        for nt in supplier.get("nt", []):
            note_number   = nt.get("ntnum")
            note_date     = nt.get("dt")
            note_value    = nt.get("val", 0.0) or 0.0
            note_type     = nt.get("typ")        # C = Credit, D = Debit
            supply_type   = nt.get("suptyp")
            pos           = nt.get("pos")
            reverse_charge = nt.get("rev")
            itc_available = nt.get("itcavl")
            diff_percent  = nt.get("diffprcnt")
            irn           = nt.get("irn")
            irn_gen_date  = nt.get("irngendate")
            source_type   = nt.get("srctyp")
            reason        = nt.get("rsn")

            # CDNRA: original note reference
            orig_note_num  = nt.get("ontnum")
            orig_note_date = nt.get("ontdt")

            items_raw = nt.get("items", [])
            if items_raw:
                taxable, cgst, sgst, igst, cess, rate = _parse_invoice_items(items_raw)
            else:
                taxable = nt.get("txval", 0) or 0.0
                cgst    = nt.get("cgst",  0) or 0.0
                sgst    = nt.get("sgst",  0) or 0.0
                igst    = nt.get("igst",  0) or 0.0
                cess    = nt.get("cess",  0) or 0.0
                rate    = None

            record: Dict[str, Any] = {
                "supplier_gstin":     ctin,
                "supplier_name":      trdnm,
                "supplier_period":    supprd,
                "supplier_file_date": supfildt,
                "note_number":        note_number,
                "note_date":          note_date,
                "note_value":         note_value,
                "note_type":          note_type,          # C / D
                "supply_type":        supply_type,
                "place_of_supply":    pos,
                "reverse_charge":     reverse_charge,
                "itc_available":      itc_available,
                "diff_percent":       diff_percent,
                "taxable_value":      taxable,
                "tax_rate":           rate,
                "cgst":               cgst,
                "sgst":               sgst,
                "igst":               igst,
                "cess":               cess,
                "irn":                irn,
                "irn_gen_date":       irn_gen_date,
                "source_type":        source_type,
                "reason":             reason,
            }
            if orig_note_num:
                record["original_note_number"] = orig_note_num
                record["original_note_date"]   = orig_note_date

            notes.append(record)

            totals["taxable"]    += taxable
            totals["cgst"]       += cgst
            totals["sgst"]       += sgst
            totals["igst"]       += igst
            totals["cess"]       += cess
            totals["note_value"] += note_value

    return notes, totals


def _parse_isd_section(isd_raw: list) -> tuple[list, Dict[str, float]]:
    """Parse ISD (Input Service Distributor) entries."""
    entries: list = []
    totals = dict(igst=0.0, cgst=0.0, sgst=0.0, cess=0.0)

    for supplier in isd_raw:
        ctin     = supplier.get("ctin")
        trdnm    = supplier.get("trdnm")
        supprd   = supplier.get("supprd")
        supfildt = supplier.get("supfildt")

        for doc in supplier.get("doclist", []):
            entries.append({
                "isd_gstin":          ctin,
                "isd_name":           trdnm,
                "supplier_period":    supprd,
                "supplier_file_date": supfildt,
                "document_number":    doc.get("docnum"),
                "document_date":      doc.get("dt"),
                "document_type":      doc.get("doctyp"),
                "itc_available":      doc.get("itcavl"),
                "igst":               doc.get("igst", 0) or 0.0,
                "cgst":               doc.get("cgst", 0) or 0.0,
                "sgst":               doc.get("sgst", 0) or 0.0,
                "cess":               doc.get("cess", 0) or 0.0,
            })
            totals["igst"] += doc.get("igst", 0) or 0.0
            totals["cgst"] += doc.get("cgst", 0) or 0.0
            totals["sgst"] += doc.get("sgst", 0) or 0.0
            totals["cess"] += doc.get("cess", 0) or 0.0

    return entries, totals


def _parse_cpsumm(cpsumm: dict) -> Dict[str, Any]:
    """
    Parse the counterparty summary block (present in status_cd=1 responses).
    Returns per-supplier summary rows for b2b and cdnr.
    """
    def _summ_rows(raw: list) -> list:
        return [
            {
                "supplier_gstin":     r.get("ctin"),
                "supplier_name":      r.get("trdnm"),
                "supplier_period":    r.get("supprd"),
                "supplier_file_date": r.get("supfildt"),
                "total_docs":         r.get("ttldocs"),
                "taxable_value":      r.get("txval", 0),
                "cgst":               r.get("cgst",  0),
                "sgst":               r.get("sgst",  0),
                "igst":               r.get("igst",  0),
                "cess":               r.get("cess",  0),
            }
            for r in (raw or [])
        ]

    return {
        "b2b":  _summ_rows(cpsumm.get("b2b",  [])),
        "cdnr": _summ_rows(cpsumm.get("cdnr", [])),
    }


def _parse_itcsumm(itcsumm: dict) -> Dict[str, Any]:
    """Flatten the nested ITC summary block into a readable dict."""
    def _tax_block(blk: dict) -> Dict[str, float]:
        return {
            "taxable_value": blk.get("txval", 0),
            "cgst":          blk.get("cgst",  0),
            "sgst":          blk.get("sgst",  0),
            "igst":          blk.get("igst",  0),
            "cess":          blk.get("cess",  0),
        }

    itcavl   = itcsumm.get("itcavl",   {})
    itcunavl = itcsumm.get("itcunavl", {})

    nonrev = itcavl.get("nonrevsup", {})
    othsup = itcavl.get("othersup",  {})
    revsup = itcavl.get("revsup",    {})
    unavl  = itcunavl.get("nonrevsup", {})

    return {
        "itc_available": {
            "non_reverse_supply": {
                "b2b":   _tax_block(nonrev.get("b2b",  {})),
                "b2ba":  _tax_block(nonrev.get("b2ba", {})),
                "cdnr":  _tax_block(nonrev.get("cdnr", {})),
                "total": _tax_block(nonrev),
            },
            "other_supply": {
                "cdnr":    _tax_block(othsup.get("cdnr",    {})),
                "cdnr_rev": _tax_block(othsup.get("cdnrrev", {})),
                "total":   _tax_block(othsup),
            },
            "reverse_supply": {
                "b2b":   _tax_block(revsup.get("b2b", {})),
                "total": _tax_block(revsup),
            },
        },
        "itc_unavailable": {
            "non_reverse_supply": {
                "b2b":   _tax_block(unavl.get("b2b", {})),
                "total": _tax_block(unavl),
            },
        },
    }


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def get_gstr2b(
    gstin: str,
    year: str,
    month: str,
    file_number: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Fetch and interpret GSTR-2B for the given GSTIN and return period.

    Handles all documented 200 response variants:
      • status_cd = "1"  — summary-only (cpsumm)  or full doc data (docdata)
      • status_cd = "3"  — paginated; first call returns fc (file count),
                           subsequent calls use file_number=1..fc
      • status_cd = "0"  — GST-level error (RET2B1023, RET2B1016, etc.)
    """
    


    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url   = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2b/{year}/{month}"

    headers = {
        "Authorization": token,
        "x-api-key":     API_KEY,
        "x-api-version": API_VERSION,
        "x-source":      "primary",
    }

    params: Dict[str, Any] = {}
    if file_number is not None:
        params["file_number"] = file_number

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        payload  = response.json()
    except Exception as e:
        return {"success": False, "message": "Failed to contact GST API", "error": str(e)}

    # ── Top-level envelope ──────────────────────────────────────────────────
    outer_data = payload.get("data", {})
    status_cd  = str(outer_data.get("status_cd", ""))

    # ── status_cd = "0"  →  GST-level error ────────────────────────────────
    if status_cd == "0":
        error_block = outer_data.get("error", {})
        return {
            "success":    False,
            "status_cd":  "0",
            "error_code": error_block.get("error_cd"),
            "message":    error_block.get("message"),
            "raw":        payload,
        }

    # ── Unwrap nested data envelope ─────────────────────────────────────────
    inner_data_wrapper = outer_data.get("data", {})
    gstin_resp = inner_data_wrapper.get("gstin")
    gen_date   = inner_data_wrapper.get("gendt")
    rtn_period = inner_data_wrapper.get("rtnprd")
    version    = inner_data_wrapper.get("version")
    fc         = inner_data_wrapper.get("fc")           # file count (paginated)
    chksum     = inner_data_wrapper.get("chksum")
    inner_data = inner_data_wrapper.get("data", {})

    # ── status_cd = "3"  →  large return, must be fetched page-by-page ──────
    # First call (no file_number) returns fc; caller must loop file_number 1..fc
    if status_cd == "3" and file_number is None:
        return {
            "success":        True,
            "status_cd":      "3",
            "pagination_required": True,
            "file_count":     fc,
            "gstin":          gstin_resp,
            "return_period":  rtn_period,
            "gen_date":       gen_date,
            "message": (
                f"Return has {fc} page(s). Re-call with file_number=1..{fc} "
                "to retrieve full invoice data."
            ),
            "raw": payload,
        }

    # ── Detect response shape ────────────────────────────────────────────────
    # Shape A  (status_cd=1, summary only):   inner_data has "cpsumm"
    # Shape B  (status_cd=1/3, full docdata): inner_data has "docdata"
    # Both shapes also carry itcsumm at the wrapper level.

    has_cpsumm  = "cpsumm"  in inner_data
    has_docdata = "docdata" in inner_data

    # ── ITC summary (present in all successful shapes) ───────────────────────
    itcsumm_raw = inner_data_wrapper.get("itcsumm", {})
    itc_summary = _parse_itcsumm(itcsumm_raw) if itcsumm_raw else None

    # ── Shape A: counterparty summary (no line-level invoices) ───────────────
    if has_cpsumm and not has_docdata:
        cpsumm = _parse_cpsumm(inner_data.get("cpsumm", {}))
        return {
            "success":        True,
            "status_cd":      status_cd,
            "response_type":  "summary",          # cpsumm — per-supplier aggregates
            "gstin":          gstin_resp,
            "return_period":  rtn_period,
            "gen_date":       gen_date,
            "version":        version,
            "checksum":       chksum,
            "file_count":     fc,
            "counterparty_summary": cpsumm,
            "itc_summary":    itc_summary,
            "raw":            payload,
        }

    # ── Shape B: full document data (line-level invoices) ────────────────────
    docdata = inner_data.get("docdata", inner_data)     # pre-Oct-2024 has no "docdata" key

    b2b_raw   = docdata.get("b2b",   [])
    b2ba_raw  = docdata.get("b2ba",  [])
    cdnr_raw  = docdata.get("cdnr",  [])
    cdnra_raw = docdata.get("cdnra", [])
    isd_raw   = docdata.get("isd",   [])

    b2b_invoices,  b2b_totals  = _parse_b2b_section(b2b_raw)
    b2ba_invoices, b2ba_totals = _parse_b2b_section(b2ba_raw)
    cdnr_notes,    cdnr_totals = _parse_cdnr_section(cdnr_raw)
    cdnra_notes,   cdnra_totals = _parse_cdnr_section(cdnra_raw)
    isd_entries,   isd_totals  = _parse_isd_section(isd_raw)

    # Grand totals across all sections
    def _add_totals(*dicts):
        result: Dict[str, float] = {}
        for d in dicts:
            for k, v in d.items():
                result[k] = result.get(k, 0.0) + v
        return result

    grand_totals = _add_totals(b2b_totals, b2ba_totals, cdnr_totals, cdnra_totals)

    return {
        "success":       True,
        "status_cd":     status_cd,
        "response_type": "documents",             # full line-level data
        "gstin":         gstin_resp,
        "return_period": rtn_period,
        "gen_date":      gen_date,
        "version":       version,
        "checksum":      chksum,
        "file_count":    fc,
        "file_number":   file_number,             # which page this response is from

        # ── Invoices ──────────────────────────────────────────────────────
        "b2b": {
            "invoices": b2b_invoices,
            "summary":  {**b2b_totals, "total_invoices": len(b2b_invoices)},
        },
        "b2ba": {
            "invoices": b2ba_invoices,
            "summary":  {**b2ba_totals, "total_invoices": len(b2ba_invoices)},
        },
        "cdnr": {
            "notes":   cdnr_notes,
            "summary": {**cdnr_totals, "total_notes": len(cdnr_notes)},
        },
        "cdnra": {
            "notes":   cdnra_notes,
            "summary": {**cdnra_totals, "total_notes": len(cdnra_notes)},
        },
        "isd": {
            "entries": isd_entries,
            "summary": {**isd_totals, "total_entries": len(isd_entries)},
        },

        # ── Cross-section roll-up ─────────────────────────────────────────
        "grand_summary": {
            "total_b2b_invoices":  len(b2b_invoices),
            "total_b2ba_invoices": len(b2ba_invoices),
            "total_cdnr_notes":    len(cdnr_notes),
            "total_cdnra_notes":   len(cdnra_notes),
            "total_isd_entries":   len(isd_entries),
            **grand_totals,
        },

        "itc_summary": itc_summary,
        "raw":         payload,
    }

def get_gstr2b_regeneration_status(gstin: str, reference_id: str) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2b/regenerate"

    headers = {
        "Authorization": token,
        "x-api-key": API_KEY,
        "x-api-version": API_VERSION,
        "x-source": "primary",
    }

    params = {"reference_id": reference_id}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        payload = response.json()
    except Exception as e:
        return {"success": False, "message": "Failed to contact GST API", "error": str(e)}

    outer_data = payload.get("data", {})
    status_cd = str(outer_data.get("status_cd", ""))

    if status_cd == "0":
        error_block = outer_data.get("error", {})
        return {
            "success": False,
            "status_cd": "0",
            "error_code": error_block.get("error_cd"),
            "message": error_block.get("message"),
            "raw": payload,
        }

    inner = outer_data.get("data", {})
    regen_status = inner.get("status_cd")

    return {
        "success": True,
        "regeneration_status": regen_status,
        "regeneration_status_label": {"P": "Processing", "C": "Completed", "F": "Failed"}.get(regen_status, regen_status),
        "error_code": inner.get("err_cd") or None,
        "error_message": inner.get("err_msg") or None,
        "raw": payload,
    }