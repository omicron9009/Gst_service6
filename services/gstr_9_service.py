import requests
from typing import Dict, Any, Optional
from config import BASE_URL, API_KEY, API_VERSION
from database.persistence import persist_service_result
from session_storage import get_session


def get_gstr9_auto_calculated(gstin: str, financial_year: str) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-9/auto-calculated"

    headers = {
        "Authorization": token,
        "x-api-key":     API_KEY,
        "x-api-version": API_VERSION,
        "x-source":      "primary",
    }

    params = {"financial_year": financial_year}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        payload = response.json()
    except Exception as e:
        return {"success": False, "message": "Failed to contact GST API", "error": str(e)}

    outer_data = payload.get("data", {})
    status_cd = str(outer_data.get("status_cd", ""))

    # status_cd = "0" → GST-level error (RT-9AS-1008, RT-9AV-1005, RT-9AS-1007, etc.)
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

    def _tax(obj: dict) -> Dict[str, float]:
        return {
            "taxable_value": obj.get("txval",  0) or 0.0,
            "igst":          obj.get("iamt",   0) or 0.0,
            "cgst":          obj.get("camt",   0) or 0.0,
            "sgst":          obj.get("samt",   0) or 0.0,
            "cess":          obj.get("csamt",  0) or 0.0,
        }

    def _txval_only(obj: dict) -> float:
        return obj.get("txval", 0) or 0.0

    # ── Table 4: Outward supplies declared in GSTR-1 ─────────────────────────
    t4 = inner.get("table4", {})
    table4 = {
        "checksum":                        t4.get("chksum"),
        "b2b_supplies":                    _tax(t4.get("b2b",     {})),
        "b2c_supplies":                    _tax(t4.get("b2c",     {})),
        "exports":                         _tax(t4.get("exp",     {})),
        "sez_supplies":                    _tax(t4.get("sez",     {})),
        "deemed_exports":                  _tax(t4.get("deemed",  {})),
        "reverse_charge":                  _tax(t4.get("rchrg",   {})),
        "ecom_operator":                   _tax(t4.get("ecom",    {})),
        "credit_notes":                    _tax(t4.get("cr_nt",   {})),
        "debit_notes":                     _tax(t4.get("dr_nt",   {})),
        "advances_tax_paid":               _tax(t4.get("at",      {})),
        "amendments_positive":             _tax(t4.get("amd_pos", {})),
        "amendments_negative":             _tax(t4.get("amd_neg", {})),
    }

    # ── Table 5: Exempt, nil-rated, non-GST outward supplies ─────────────────
    t5 = inner.get("table5", {})
    table5 = {
        "checksum":            t5.get("chksum"),
        "nil_rated":           _txval_only(t5.get("nil",      {})),
        "exempt":              _txval_only(t5.get("exmt",     {})),
        "non_gst":             _txval_only(t5.get("non_gst",  {})),
        "zero_rated":          _txval_only(t5.get("zero_rtd", {})),
        "sez":                 _txval_only(t5.get("sez",      {})),
        "reverse_charge":      _txval_only(t5.get("rchrg",    {})),
        "ecom_section_14":     _txval_only(t5.get("ecom_14",  {})),
        "credit_notes":        _txval_only(t5.get("cr_nt",    {})),
        "debit_notes":         _txval_only(t5.get("dr_nt",    {})),
        "amendments_positive": _txval_only(t5.get("amd_pos",  {})),
        "amendments_negative": _txval_only(t5.get("amd_neg",  {})),
    }

    # ── Table 6: ITC availed as declared in GSTR-3B ──────────────────────────
    t6 = inner.get("table6", {})
    table6 = {
        "checksum":              t6.get("chksum"),
        "itc_from_gstr3b":       _tax(t6.get("itc_3b", {})),
        "itc_from_isd":          _tax(t6.get("isd",    {})),
        "tran1_credit": {
            "cgst": t6.get("tran1", {}).get("camt", 0) or 0.0,
            "sgst": t6.get("tran1", {}).get("samt", 0) or 0.0,
        },
        "tran2_credit": {
            "cgst": t6.get("tran2", {}).get("camt", 0) or 0.0,
            "sgst": t6.get("tran2", {}).get("samt", 0) or 0.0,
        },
    }

    # ── Table 8: ITC as per GSTR-2B ──────────────────────────────────────────
    t8 = inner.get("table8", {})
    table8 = {
        "checksum":       t8.get("chksum"),
        "itc_as_per_2b":  _tax(t8.get("itc_2b", {})),
    }

    # ── Table 9: Tax paid as declared in GSTR-3B ─────────────────────────────
    t9 = inner.get("table9", {})

    def _tax9(component_key: str, obj: dict) -> Dict[str, float]:
        """Normalise table9 per-component blocks (iamt/camt/samt/csamt each have their own keys)."""
        return {
            "tax_payable":         obj.get("txpyble",          0) or 0.0,
            "paid_in_cash":        obj.get("txpaid_cash",       0) or 0.0,
            "paid_via_igst_itc":   obj.get("tax_paid_itc_iamt", 0) or 0.0,
            "paid_via_cgst_itc":   obj.get("tax_paid_itc_camt", 0) or 0.0,
            "paid_via_sgst_itc":   obj.get("tax_paid_itc_samt", 0) or 0.0,
            "paid_via_cess_itc":   obj.get("tax_paid_itc_csamt",0) or 0.0,
        }

    table9 = {
        "checksum": t9.get("chksum"),
        "igst":     _tax9("iamt",  t9.get("iamt",  {})),
        "cgst":     _tax9("camt",  t9.get("camt",  {})),
        "sgst":     _tax9("samt",  t9.get("samt",  {})),
        "cess":     _tax9("csamt", t9.get("csamt", {})),
        "interest": {
            "tax_payable":  t9.get("intr", {}).get("txpyble",    0) or 0.0,
            "paid_in_cash": t9.get("intr", {}).get("txpaid_cash",0) or 0.0,
        },
        "late_fee": {
            "tax_payable":  t9.get("fee", {}).get("txpyble",    0) or 0.0,
            "paid_in_cash": t9.get("fee", {}).get("txpaid_cash",0) or 0.0,
        },
    }

    return {
        "success":          True,
        "status_cd":        status_cd,
        "gstin":            inner.get("gstin"),
        "financial_period": inner.get("fp"),
        "aggregate_turnover": inner.get("aggTurnover"),
        "hsn_min_length":   inner.get("hsnMinLen"),
        "table4_outward_supplies":          table4,
        "table5_exempt_nil_non_gst":        table5,
        "table6_itc_availed":               table6,
        "table8_itc_as_per_2b":             table8,
        "table9_tax_paid":                  table9,
        "raw": payload,
    }


def _parse_invoice(doc: dict) -> Dict[str, Any]:
    return {
        "invoice_number":          doc.get("inum"),
        "invoice_date":            doc.get("idt"),
        "original_invoice_number": doc.get("oinum") or None,
        "original_invoice_date":   doc.get("oidt")  or None,
        "note_number":             doc.get("nt_num") or None,
        "note_date":               doc.get("nt_dt")  or None,
        "note_type":               doc.get("ntty")   or None,
        "invoice_type":            doc.get("inv_typ") or None,
        "place_of_supply":         doc.get("pos"),
        "reverse_charge":          doc.get("rchrg"),
        "is_eligible":             doc.get("iseligible"),
        "ineligibility_reason":    doc.get("reason") or None,
        "taxable_value":           doc.get("txval", 0) or 0.0,
        "invoice_value":           doc.get("val",   0) or 0.0,
        "igst":                    doc.get("iamt",  0) or 0.0,
        "cgst":                    doc.get("camt",  0) or 0.0,
        "sgst":                    doc.get("samt",  0) or 0.0,
        "cess":                    doc.get("csamt", 0) or 0.0,
    }


def _parse_supplier_group(entries: list) -> list:
    result = []
    for entry in (entries or []):
        result.append({
            "supplier_gstin": entry.get("stin"),
            "filing_date":    entry.get("filingdt"),
            "return_period":  entry.get("rtnPrd"),
            "documents": [_parse_invoice(d) for d in entry.get("documents", [])],
        })
    return result


def get_gstr9_table8a(gstin: str, financial_year: str, file_number: Optional[str] = None) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-9/table-8a"

    headers = {
        "Authorization": token,
        "x-api-key":     API_KEY,
        "x-api-version": API_VERSION,
        "x-source":      "primary",
    }

    params: Dict[str, Any] = {"financial_year": financial_year}
    if file_number is not None:
        params["file_number"] = file_number

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        payload = response.json()
    except Exception as e:
        return {"success": False, "message": "Failed to contact GST API", "error": str(e)}

    outer_data = payload.get("data", {})
    status_cd = str(outer_data.get("status_cd", ""))

    # status_cd = "0" → error (e.g. RT-9AG-1019 No records found)
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

    # ── Pagination metadata ───────────────────────────────────────────────────
    # docid = current file number returned; if present, multiple files may exist
    doc_id = inner.get("docid")

    # ── B2B: Regular inward supplies from registered suppliers ────────────────
    b2b = _parse_supplier_group(inner.get("b2b", []))

    # ── B2BA: Amendments to B2B invoices (includes oinum/oidt for original ref)
    b2ba = _parse_supplier_group(inner.get("b2ba", []))

    # ── CDN: Credit/Debit notes from registered suppliers ────────────────────
    cdn = _parse_supplier_group(inner.get("cdn", []))

    # ── Grand summary across all sections ────────────────────────────────────
    def _sum_section(entries: list) -> Dict[str, float]:
        totals = {"taxable_value": 0.0, "igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0, "invoice_count": 0}
        for supplier in entries:
            for doc in supplier["documents"]:
                totals["taxable_value"] += doc["taxable_value"]
                totals["igst"]          += doc["igst"]
                totals["cgst"]          += doc["cgst"]
                totals["sgst"]          += doc["sgst"]
                totals["cess"]          += doc["cess"]
                totals["invoice_count"] += 1
        return totals

    return {
        "success":        True,
        "status_cd":      status_cd,
        "gstin":          inner.get("gstin"),
        "financial_year": inner.get("fy"),
        "file_number":    doc_id,
        "b2b":            b2b,
        "b2ba":           b2ba,
        "cdn":            cdn,
        "summary": {
            "b2b":  _sum_section(b2b),
            "b2ba": _sum_section(b2ba),
            "cdn":  _sum_section(cdn),
        },
        "raw": payload,
    }

def get_gstr9_details(gstin: str, financial_year: str) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-9"

    headers = {
        "Authorization": token,
        "x-api-key":     API_KEY,
        "x-api-version": API_VERSION,
        "x-source":      "primary",
    }

    params = {"financial_year": financial_year}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        payload = response.json()
    except Exception as e:
        return {"success": False, "message": "Failed to contact GST API", "error": str(e)}

    outer_data = payload.get("data", {})
    status_cd = str(outer_data.get("status_cd", ""))

    # status_cd = "0" → error (e.g. RT-9AS-1008 GSTR-1/GSTR-3B not filed)
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

    def _tax(obj: dict) -> Dict[str, float]:
        return {
            "taxable_value": obj.get("txval",  0) or 0.0,
            "igst":          obj.get("iamt",   0) or 0.0,
            "cgst":          obj.get("camt",   0) or 0.0,
            "sgst":          obj.get("samt",   0) or 0.0,
            "cess":          obj.get("csamt",  0) or 0.0,
        }

    def _txval_only(obj: dict) -> float:
        return obj.get("txval", 0) or 0.0

    def _tax_no_txval(obj: dict) -> Dict[str, float]:
        return {
            "igst": obj.get("iamt",  0) or 0.0,
            "cgst": obj.get("camt",  0) or 0.0,
            "sgst": obj.get("samt",  0) or 0.0,
            "cess": obj.get("csamt", 0) or 0.0,
        }

    # ── Table 4: Outward supplies (taxable) ───────────────────────────────────
    t4 = inner.get("table4", {})
    table4 = {
        "checksum":                    t4.get("chksum"),
        "b2b_supplies":                _tax(t4.get("b2b",          {})),
        "b2c_supplies":                _tax(t4.get("b2c",          {})),
        "credit_notes":                _tax(t4.get("cr_nt",        {})),
        "subtotal_a_to_g1":            _tax(t4.get("sub_totalAG1", {})),
        "subtotal_i_to_l_deductions":  _tax(t4.get("sub_totalIL",  {})),
        "net_taxable_turnover":        _tax(t4.get("sup_adv",      {})),
    }

    # ── Table 5: Exempt, nil-rated, non-GST outward supplies ─────────────────
    t5 = inner.get("table5", {})
    table5 = {
        "checksum":             t5.get("chksum"),
        "nil_rated":            _txval_only(t5.get("nil",          {})),
        "exempt":               _txval_only(t5.get("exmt",         {})),
        "non_gst":              _txval_only(t5.get("non_gst",      {})),
        "zero_rated":           _txval_only(t5.get("zero_rtd",     {})),
        "sez":                  _txval_only(t5.get("sez",          {})),
        "reverse_charge":       _txval_only(t5.get("rchrg",        {})),
        "ecom_section_14":      _txval_only(t5.get("ecom_14",      {})),
        "credit_notes":         _txval_only(t5.get("cr_nt",        {})),
        "debit_notes":          _txval_only(t5.get("dr_nt",        {})),
        "amendments_positive":  _txval_only(t5.get("amd_pos",      {})),
        "amendments_negative":  _txval_only(t5.get("amd_neg",      {})),
        "subtotal_a_to_f":      _txval_only(t5.get("sub_totalAF",  {})),
        "subtotal_h_to_k":      _txval_only(t5.get("sub_totalHK",  {})),
        "turnover_tax_not_paid":_txval_only(t5.get("tover_tax_np", {})),
        "total_turnover":       _tax(t5.get("total_tover",         {})),
    }

    # ── Table 6: ITC availed ──────────────────────────────────────────────────
    t6 = inner.get("table6", {})

    ITC_TYPE_LABELS = {"cg": "Capital Goods", "is": "Input Services", "ip": "Inputs"}
    supp_non_rchrg = [
        {
            **_tax_no_txval(row),
            "itc_type":       row.get("itc_typ"),
            "itc_type_label": ITC_TYPE_LABELS.get(row.get("itc_typ"), row.get("itc_typ")),
        }
        for row in t6.get("supp_non_rchrg", [])
    ]

    table6 = {
        "checksum":              t6.get("chksum"),
        "itc_from_gstr3b":       _tax_no_txval(t6.get("itc_3b",           {})),
        "non_reverse_charge_itc": supp_non_rchrg,
        "subtotal_b_to_h":       _tax_no_txval(t6.get("sub_totalBH",      {})),
        "subtotal_k_to_m":       _tax_no_txval(t6.get("sub_totalKM",      {})),
        "total_itc_availed":     _tax_no_txval(t6.get("total_itc_availed", {})),
        "difference_6b_vs_3b":   _tax_no_txval(t6.get("difference",        {})),
    }

    # ── Table 7: ITC reversed & ineligible ───────────────────────────────────
    t7 = inner.get("table7", {})
    table7 = {
        "checksum":             t7.get("chksum"),
        "net_itc_available":    _tax_no_txval(t7.get("net_itc_aval",  {})),
        "rule_37_reversal":     _tax_no_txval(t7.get("rule37",        {})),
        "rule_39_reversal":     _tax_no_txval(t7.get("rule39",        {})),
        "rule_42_reversal":     _tax_no_txval(t7.get("rule42",        {})),
        "rule_43_reversal":     _tax_no_txval(t7.get("rule43",        {})),
        "section_17_reversal":  _tax_no_txval(t7.get("sec17",         {})),
        "tran1_reversal": {
            "cgst": t7.get("revsl_tran1", {}).get("camt", 0) or 0.0,
            "sgst": t7.get("revsl_tran1", {}).get("samt", 0) or 0.0,
        },
        "tran2_reversal": {
            "cgst": t7.get("revsl_tran2", {}).get("camt", 0) or 0.0,
            "sgst": t7.get("revsl_tran2", {}).get("samt", 0) or 0.0,
        },
        "total_itc_reversed":   _tax_no_txval(t7.get("tot_itc_revd",  {})),
    }

    # ── Table 8: ITC comparison (GSTR-2B vs GSTR-3B) ────────────────────────
    t8 = inner.get("table8", {})
    table8 = {
        "checksum":                        t8.get("chksum"),
        "itc_as_per_2b":                   _tax_no_txval(t8.get("itc_2b",          {})),
        "itc_net_availed":                 _tax_no_txval(t8.get("itc_tot",          {})),
        "itc_on_inward_supplies":          _tax_no_txval(t8.get("itc_inwd_supp",    {})),
        "itc_not_availed":                 _tax_no_txval(t8.get("itc_nt_availd",    {})),
        "itc_ineligible":                  _tax_no_txval(t8.get("itc_nt_eleg",      {})),
        "itc_lapsed":                      _tax_no_txval(t8.get("tot_itc_lapsed",   {})),
        "iog_itc_availed":                 _tax_no_txval(t8.get("iog_itc_availd",   {})),
        "iog_itc_not_availed":             _tax_no_txval(t8.get("iog_itc_ntavaild", {})),
        "iog_tax_paid":                    _tax_no_txval(t8.get("iog_taxpaid",      {})),
        "difference_abc_2b_vs_3b":         _tax_no_txval(t8.get("differenceABC",    {})),
        "difference_gh_itc_vs_ineligible": _tax_no_txval(t8.get("differenceGH",     {})),
    }

    # ── Table 9: Tax payable vs paid ─────────────────────────────────────────
    t9 = inner.get("table9", {})

    def _tax9(obj: dict) -> Dict[str, float]:
        return {
            "tax_payable":         obj.get("txpyble",           0) or 0.0,
            "paid_in_cash":        obj.get("txpaid_cash",        0) or 0.0,
            "paid_via_igst_itc":   obj.get("tax_paid_itc_iamt",  0) or 0.0,
            "paid_via_cgst_itc":   obj.get("tax_paid_itc_camt",  0) or 0.0,
            "paid_via_sgst_itc":   obj.get("tax_paid_itc_samt",  0) or 0.0,
            "paid_via_cess_itc":   obj.get("tax_paid_itc_csamt", 0) or 0.0,
        }

    table9 = {
        "checksum": t9.get("chksum"),
        "igst":     _tax9(t9.get("iamt",  {})),
        "cgst":     _tax9(t9.get("camt",  {})),
        "sgst":     _tax9(t9.get("samt",  {})),
        "cess":     _tax9(t9.get("csamt", {})),
        "interest": {
            "tax_payable":  t9.get("intr", {}).get("txpyble",    0) or 0.0,
            "paid_in_cash": t9.get("intr", {}).get("txpaid_cash",0) or 0.0,
        },
        "late_fee": {
            "tax_payable":  t9.get("fee", {}).get("txpyble",    0) or 0.0,
            "paid_in_cash": t9.get("fee", {}).get("txpaid_cash",0) or 0.0,
        },
        "penalty": {
            "tax_payable": t9.get("pen",   {}).get("txpyble", 0) or 0.0,
        },
        "other": {
            "tax_payable": t9.get("other", {}).get("txpyble", 0) or 0.0,
        },
    }

    # ── Table 10: Total turnover reconciliation ───────────────────────────────
    t10 = inner.get("table10", {})
    table10 = {
        "total_turnover": _tax(t10.get("total_turnover", {})),
    }

    # ── Table 17: HSN-wise summary of outward supplies ───────────────────────
    t17 = inner.get("table17", {})
    table17 = {
        "checksum": t17.get("chksum"),
        "hsn_items": [
            {
                "hsn_sac":        item.get("hsn_sc"),
                "description":    item.get("desc"),
                "tax_rate":       item.get("rt"),
                "is_concessional": item.get("isconcesstional"),
                "taxable_value":  item.get("txval",  0) or 0.0,
                "igst":           item.get("iamt",   0) or 0.0,
                "cgst":           item.get("camt",   0) or 0.0,
                "sgst":           item.get("samt",   0) or 0.0,
                "cess":           item.get("csamt",  0) or 0.0,
            }
            for item in t17.get("items", [])
        ],
    }

    return {
        "success":           True,
        "status_cd":         status_cd,
        "gstin":             inner.get("gstin"),
        "financial_period":  inner.get("fp"),
        "aggregate_turnover": inner.get("aggTurnover"),
        "table4_outward_taxable_supplies": table4,
        "table5_exempt_nil_non_gst":       table5,
        "table6_itc_availed":              table6,
        "table7_itc_reversed":             table7,
        "table8_itc_comparison":           table8,
        "table9_tax_payable_vs_paid":      table9,
        "table10_turnover_reconciliation": table10,
        "table17_hsn_summary":             table17,
        "raw": payload,
    }


get_gstr9_auto_calculated = persist_service_result("get_gstr9_auto_calculated")(get_gstr9_auto_calculated)
get_gstr9_table8a = persist_service_result("get_gstr9_table8a")(get_gstr9_table8a)
get_gstr9_details = persist_service_result("get_gstr9_details")(get_gstr9_details)


