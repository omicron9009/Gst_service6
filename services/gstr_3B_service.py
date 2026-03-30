import requests
from typing import Dict, Any, Optional
from config import BASE_URL, API_KEY, API_VERSION
from database.persistence import persist_service_result
from session_storage import get_session





def get_gstr3b_details(gstin: str, year: str, month: str) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-3b/{year}/{month}"

    headers = {
        "Authorization": token,
        "x-api-key": API_KEY,
        "x-api-version": API_VERSION,
        "x-source": "primary",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        payload = response.json()
    except Exception as e:
        return {"success": False, "message": "Failed to contact GST API", "error": str(e)}

    outer_data = payload.get("data", {})
    status_cd = str(outer_data.get("status_cd", ""))

    # status_cd = "0" → GST-level error (e.g. RT-R3BQ1004 GSTR-1 not filed)
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
            "taxable_value": obj.get("txval", 0) or 0.0,
            "igst":          obj.get("iamt",  0) or 0.0,
            "cgst":          obj.get("camt",  0) or 0.0,
            "sgst":          obj.get("samt",  0) or 0.0,
            "cess":          obj.get("csamt", 0) or 0.0,
        }

    def _tax_component(obj: dict) -> Dict[str, float]:
        return {
            "tax":      obj.get("tx",   0) or 0.0,
            "interest": obj.get("intr", 0) or 0.0,
            "fee":      obj.get("fee",  0) or 0.0,
        }

    def _pos_rows(rows: list) -> list:
        return [
            {
                "place_of_supply": r.get("pos"),
                "taxable_value":   r.get("txval", 0) or 0.0,
                "igst":            r.get("iamt",  0) or 0.0,
            }
            for r in (rows or [])
        ]

    # ── Supply Details ───────────────────────────────────────────────────────
    sup = inner.get("sup_details", {})
    supply_details = {
        "outward_taxable_supplies":     _tax(sup.get("osup_det",      {})),
        "outward_zero_rated":           _tax(sup.get("osup_zero",     {})),
        "outward_nil_exempt_non_gst":   _tax(sup.get("osup_nil_exmp", {})),
        "outward_non_gst":              _tax(sup.get("osup_nongst",   {})),
        "inward_reverse_charge":        _tax(sup.get("isup_rev",      {})),
    }

    # ── Inter-state Supplies (Table 3.2) ─────────────────────────────────────
    inter = inner.get("inter_sup", {})
    inter_state_supplies = {
        "unregistered_persons":  _pos_rows(inter.get("unreg_details", [])),
        "composition_dealers":   _pos_rows(inter.get("comp_details",  [])),
        "uin_holders":           _pos_rows(inter.get("uin_details",   [])),
    }

    # ── Eligible ITC (Table 4) ───────────────────────────────────────────────
    itc = inner.get("itc_elg", {})

    ITC_AVL_LABELS = {
        "IMPG": "Import of goods",
        "IMPS": "Import of services",
        "ISRC": "Inward supplies from ISD",
        "ISD":  "ISD credits",
        "OTH":  "All other ITC",
    }
    ITC_INELG_LABELS = {
        "RUL": "As per rules 42 & 43 of CGST Rules",
        "OTH": "Others",
    }

    itc_eligible = {
        "itc_available": [
            {**_tax(row), "type": row.get("ty"), "label": ITC_AVL_LABELS.get(row.get("ty"), row.get("ty"))}
            for row in itc.get("itc_avl", [])
        ],
        "itc_reversed": [
            {**_tax(row), "type": row.get("ty"), "label": ITC_INELG_LABELS.get(row.get("ty"), row.get("ty"))}
            for row in itc.get("itc_rev", [])
        ],
        "itc_ineligible": [
            {**_tax(row), "type": row.get("ty"), "label": ITC_INELG_LABELS.get(row.get("ty"), row.get("ty"))}
            for row in itc.get("itc_inelg", [])
        ],
        "itc_net": _tax(itc.get("itc_net", {})),
    }

    # ── Inward Supplies (exempt from ITC — Table 5) ──────────────────────────
    inward_raw = inner.get("inward_sup", {}).get("isup_details", [])
    inward_supplies = [
        {
            "type":        r.get("ty"),
            "inter_state": r.get("inter", 0) or 0.0,
            "intra_state": r.get("intra", 0) or 0.0,
        }
        for r in inward_raw
    ]

    # ── Interest & Late Fee (Table 5.1) ──────────────────────────────────────
    intr_ltfee = inner.get("intr_ltfee", {})
    interest_late_fee = {
        "interest":  _tax(intr_ltfee.get("intr_details",  {})),
        "late_fee":  _tax(intr_ltfee.get("ltfee_details", {})),
    }

    # ── Tax Payment (Table 6) ─────────────────────────────────────────────────
    tx_pmt = inner.get("tx_pmt", {})

    TRANS_LABELS = {
        30002: "Other than Reverse Charge",
        30003: "Reverse Charge / u/s 9(5)",
    }

    def _payment_row(row: dict) -> Dict[str, Any]:
        return {
            "transaction_type":        row.get("trans_typ"),
            "transaction_description": row.get("tran_desc") or TRANS_LABELS.get(row.get("trans_typ")),
            "liability_ledger_id":     row.get("liab_ldg_id"),
            "igst":  _tax_component(row.get("igst",  {})),
            "cgst":  _tax_component(row.get("cgst",  {})),
            "sgst":  _tax_component(row.get("sgst",  {})),
            "cess":  _tax_component(row.get("cess",  {})),
        }

    net_tax_payable = [_payment_row(r) for r in tx_pmt.get("net_tax_pay", [])]
    tax_payable     = [_payment_row(r) for r in tx_pmt.get("tx_py",       [])]

    # Cash paid
    cash_paid = [
        {
            "transaction_type":    r.get("trans_typ"),
            "liability_ledger_id": r.get("liab_ldg_id"),
            "igst_paid":  r.get("ipd",      0) or 0.0,
            "cgst_paid":  r.get("cpd",      0) or 0.0,
            "sgst_paid":  r.get("spd",      0) or 0.0,
            "cess_paid":  r.get("cspd",     0) or 0.0,
            "igst_interest_paid": r.get("i_intrpd", 0) or 0.0,
            "cgst_interest_paid": r.get("c_intrpd", 0) or 0.0,
            "sgst_interest_paid": r.get("s_intrpd", 0) or 0.0,
            "igst_fee_paid":      r.get("i_lfeepd", 0) or 0.0,
            "cgst_fee_paid":      r.get("c_lfeepd", 0) or 0.0,
            "sgst_fee_paid":      r.get("s_lfeepd", 0) or 0.0,
        }
        for r in tx_pmt.get("pdcash", [])
    ]

    # ITC utilised
    pditc = tx_pmt.get("pditc", {})
    itc_utilised = {
        "liability_ledger_id": pditc.get("liab_ldg_id"),
        "transaction_type":    pditc.get("trans_typ"),
        "igst_from_igst":      pditc.get("i_pdi",  0) or 0.0,
        "igst_from_cgst":      pditc.get("i_pdc",  0) or 0.0,
        "igst_from_sgst":      pditc.get("i_pds",  0) or 0.0,
        "cgst_from_igst":      pditc.get("c_pdi",  0) or 0.0,
        "cgst_from_cgst":      pditc.get("c_pdc",  0) or 0.0,
        "sgst_from_igst":      pditc.get("s_pdi",  0) or 0.0,
        "sgst_from_sgst":      pditc.get("s_pds",  0) or 0.0,
        "cess_from_cess":      pditc.get("cs_pdcs", 0) or 0.0,
    }

    return {
        "success":        True,
        "status_cd":      status_cd,
        "gstin":          inner.get("gstin"),
        "return_period":  inner.get("ret_period"),
        "supply_details":        supply_details,
        "inter_state_supplies":  inter_state_supplies,
        "eligible_itc":          itc_eligible,
        "inward_supplies":       inward_supplies,
        "interest_and_late_fee": interest_late_fee,
        "tax_payment": {
            "net_tax_payable": net_tax_payable,
            "tax_payable":     tax_payable,
            "cash_paid":       cash_paid,
            "itc_utilised":    itc_utilised,
        },
        "raw": payload,
    }



def get_gstr3b_auto_liability(gstin: str, year: str, month: str) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-3b/{year}/{month}/auto-liability-calc"

    headers = {
        "Authorization": token,
        "x-api-key": API_KEY,
        "x-api-version": API_VERSION,
        "x-source": "primary",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        payload = response.json()
    except Exception as e:
        return {"success": False, "message": "Failed to contact GST API", "error": str(e)}

    outer_data = payload.get("data", {})
    status_cd = str(outer_data.get("status_cd", ""))

    # status_cd = "0" → GST-level error (e.g. RT-R3BQ1004 GSTR-1 not filed)
    if status_cd == "0":
        error_block = outer_data.get("error", {})
        return {
            "success": False,
            "status_cd": "0",
            "error_code": error_block.get("error_cd"),
            "message": error_block.get("message"),
            "raw": payload,
        }

    # status_cd = "1" → success, parse r3bautopop
    inner = outer_data.get("data", {})
    r3b = inner.get("r3bautopop", {})
    liabitc = r3b.get("liabitc", {})
    elgitc = liabitc.get("elgitc", {})
    sup_details = liabitc.get("sup_details", {})
    inter_sup = liabitc.get("inter_sup", {})

    def _tax_block(obj: dict) -> Dict[str, float]:
        return {
            "igst":  obj.get("iamt",  0) or 0.0,
            "cgst":  obj.get("camt",  0) or 0.0,
            "sgst":  obj.get("samt",  0) or 0.0,
            "cess":  obj.get("csamt", 0) or 0.0,
            "taxable_value": obj.get("txval", 0) or 0.0,
        }

    def _itc_section(section: dict) -> Dict[str, Any]:
        det = section.get("det", {})
        return {
            "itc_available":          _tax_block(det.get("itcavl",    {})),
            "itc_available_cn":       _tax_block(det.get("itcavl_cn", {})),
            "itc_unavailable":        _tax_block(det.get("itcunavl",  {})),
            "subtotal":               _tax_block(section.get("subtotal", {})),
        }

    def _pos_rows(rows: list) -> list:
        return [
            {
                "place_of_supply": r.get("pos"),
                "taxable_value":   r.get("txval", 0) or 0.0,
                "igst":            r.get("iamt",  0) or 0.0,
            }
            for r in (rows or [])
            if r.get("pos")  # skip blank placeholder rows
        ]

    def _inter_sup_section(section: dict) -> Dict[str, Any]:
        det = section.get("det", {})
        return {
            "source_tables": {
                k: _pos_rows(v) for k, v in det.items()
            },
            "subtotal": _pos_rows(section.get("subtotal", [])),
        }

    def _sup_section(section: dict) -> Dict[str, Any]:
        det = section.get("det", {})
        return {
            "source_tables": {
                k: _tax_block(v) for k, v in det.items()
            },
            "subtotal": _tax_block(section.get("subtotal", {})),
        }

    return {
        "success":      True,
        "status_cd":    status_cd,
        "gstin":        liabitc.get("gstin"),
        "return_period": liabitc.get("ret_period"),
        "r1_filed_date":  inner.get("r1fildt"),
        "r2b_gen_date":   inner.get("r2bgendt"),
        "r3b_gen_date":   inner.get("r3bgendt"),
        "errors":         r3b.get("error", []),

        # Eligible ITC — 4 sub-sections mapped to GSTR-3B table rows
        "eligible_itc": {
            "itc_4a1_import_goods":        _itc_section(elgitc.get("itc4a1", {})),
            "itc_4a3_inward_reverse_charge": _itc_section(elgitc.get("itc4a3", {})),
            "itc_4a4_inward_isd":          _itc_section(elgitc.get("itc4a4", {})),
            "itc_4a5_all_other_itc":       _itc_section(elgitc.get("itc4a5", {})),
            "itc_4d2_ineligible":          _itc_section(elgitc.get("itc4d2", {})),
        },

        # Outward supply details — 3B table 3.1 sections
        "supply_details": {
            "osup_3_1a_taxable_outward":         _sup_section(sup_details.get("osup_3_1a", {})),
            "osup_3_1b_zero_rated_supply":       _sup_section(sup_details.get("osup_3_1b", {})),
            "osup_3_1c_nil_exempt_non_gst":      _sup_section(sup_details.get("osup_3_1c", {})),
            "osup_3_1e_non_gst_outward":         _sup_section(sup_details.get("osup_3_1e", {})),
            "isup_3_1d_inward_reverse_charge":   _sup_section(sup_details.get("isup_3_1d", {})),
        },

        # Inter-state supply details — 3B table 3.2 (pos-wise breakup)
        "inter_state_supplies": {
            "osup_unreg_3_2_unregistered":   _inter_sup_section(inter_sup.get("osup_unreg_3_2", {})),
            "osup_comp_3_2_composition":     _inter_sup_section(inter_sup.get("osup_comp_3_2", {})),
            "osup_uin_3_2_uin_holders":      _inter_sup_section(inter_sup.get("osup_uin_3_2",  {})),
        },

        "raw": payload,
    }


get_gstr3b_details = persist_service_result("get_gstr3b_details")(get_gstr3b_details)
get_gstr3b_auto_liability = persist_service_result("get_gstr3b_auto_liability")(get_gstr3b_auto_liability)


