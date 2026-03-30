
# Completely Written 


import requests
from typing import Dict, Any, Optional
from config import BASE_URL, API_KEY, API_VERSION
from database.persistence import persist_service_result
from session_storage import get_session


def get_cash_itc_balance(gstin: str, year: str, month: str) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/ledgers/bal/{year}/{month}"

    headers = {
        "Authorization": token,
        "x-api-key":     API_KEY,
        "x-api-version": API_VERSION,
        "x-source":      "primary",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        payload = response.json()
    except Exception as e:
        return {"success": False, "message": "Failed to contact GST API", "error": str(e)}

    outer_data = payload.get("data", {})
    status_cd = str(outer_data.get("status_cd", ""))

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

    def _cash_component(obj: dict) -> Dict[str, float]:
        return {
            "tax":      obj.get("tx",   0) or 0.0,
            "interest": obj.get("intr", 0) or 0.0,
            "penalty":  obj.get("pen",  0) or 0.0,
            "fee":      obj.get("fee",  0) or 0.0,
            "other":    obj.get("oth",  0) or 0.0,
        }

    cash = inner.get("cash_bal", {})
    itc  = inner.get("itc_bal",  {})
    blck = inner.get("itc_blck_bal", {})

    return {
        "success":   True,
        "status_cd": status_cd,
        "gstin":     inner.get("gstin"),

        # ── Cash Ledger Balance ───────────────────────────────────────────────
        # Available cash broken down by tax type and sub-head (tax/interest/penalty/fee/other)
        "cash_balance": {
            "igst": {
                **_cash_component(cash.get("igst", {})),
                "total": cash.get("igst_tot_bal", 0) or 0.0,
            },
            "cgst": {
                **_cash_component(cash.get("cgst", {})),
                "total": cash.get("cgst_tot_bal", 0) or 0.0,
            },
            "sgst": {
                **_cash_component(cash.get("sgst", {})),
                "total": cash.get("sgst_tot_bal", 0) or 0.0,
            },
            "cess": {
                **_cash_component(cash.get("cess", {})),
                "total": cash.get("cess_tot_bal", 0) or 0.0,
            },
        },

        # ── ITC Ledger Balance ────────────────────────────────────────────────
        # Net available Input Tax Credit per tax head
        "itc_balance": {
            "igst": itc.get("igst_bal", 0) or 0.0,
            "cgst": itc.get("cgst_bal", 0) or 0.0,
            "sgst": itc.get("sgst_bal", 0) or 0.0,
            "cess": itc.get("cess_bal", 0) or 0.0,
        },

        # ── Blocked ITC Balance ───────────────────────────────────────────────
        # ITC currently blocked / under scrutiny per tax head
        "itc_blocked_balance": {
            "igst": blck.get("igst_blck_bal", 0) or 0.0,
            "cgst": blck.get("cgst_blck_bal", 0) or 0.0,
            "sgst": blck.get("sgst_blck_bal", 0) or 0.0,
            "cess": blck.get("cess_blck_bal", 0) or 0.0,
        },

        "raw": payload,
    }



def get_cash_ledger(gstin: str, from_date: str, to_date: str) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/ledgers/cash"

    headers = {
        "Authorization": token,
        "x-api-key":     API_KEY,
        "x-api-version": API_VERSION,
        "x-source":      "primary",
    }

    params = {
        "from": from_date,
        "to":   to_date,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        payload = response.json()
    except Exception as e:
        return {"success": False, "message": "Failed to contact GST API", "error": str(e)}

    outer_data = payload.get("data", {})
    status_cd = str(outer_data.get("status_cd", ""))

    # status_cd = "0" → GST-level error (e.g. LG9089 To date cannot be beyond current date)
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

    def _ledger_balance(obj: dict) -> Dict[str, float]:
        # Each tax-head balance block has: tx, intr, pen, fee, oth, tot
        return {
            "tax":      obj.get("tx",   0) or 0.0,
            "interest": obj.get("intr", 0) or 0.0,
            "penalty":  obj.get("pen",  0) or 0.0,
            "fee":      obj.get("fee",  0) or 0.0,
            "other":    obj.get("oth",  0) or 0.0,
            "total":    obj.get("tot",  0) or 0.0,
        }

    def _parse_balance_block(block: dict) -> Dict[str, Any]:
        return {
            "igst":              _ledger_balance(block.get("igstbal", {})),
            "cgst":              _ledger_balance(block.get("cgstbal", {})),
            "sgst":              _ledger_balance(block.get("sgstbal", {})),
            "cess":              _ledger_balance(block.get("cessbal", {})),
            "total_range_balance": block.get("tot_rng_bal", 0) or 0.0,
        }

    # ── Transactions ──────────────────────────────────────────────────────────
    # tr is an array of transaction entries for the period.
    # The API returns [] when no transactions exist in the date range.
    transactions = inner.get("tr", []) or []

    return {
        "success":   True,
        "status_cd": status_cd,
        "gstin":     inner.get("gstin"),
        "from_date": inner.get("fr_dt"),
        "to_date":   inner.get("to_dt"),

        # Opening balance at the start of the requested period
        "opening_balance": _parse_balance_block(inner.get("op_bal", {})),

        # Closing balance at the end of the requested period
        "closing_balance": _parse_balance_block(inner.get("cl_bal", {})),

        # Individual transactions within the period (empty list if none)
        "transactions": transactions,

        "raw": payload,
    }

def get_itc_ledger(gstin: str, from_date: str, to_date: str) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/ledgers/itc"

    headers = {
        "Authorization": token,
        "x-api-key":     API_KEY,
        "x-api-version": API_VERSION,
        "x-source":      "primary",
    }

    params = {
        "from": from_date,
        "to":   to_date,
    }

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
            "success":    False,
            "status_cd":  "0",
            "error_code": error_block.get("error_cd"),
            "message":    error_block.get("message"),
            "raw":        payload,
        }

    inner      = outer_data.get("data", {})
    ledger     = inner.get("itcLdgDtls", {})
    prov_crd   = inner.get("provCrdBalList", {})

    def _balance_block(obj: dict) -> Dict[str, float]:
        # ITC balance blocks only have one number per tax head (no sub-heads)
        return {
            "igst":              obj.get("igstTaxBal", 0) or 0.0,
            "cgst":              obj.get("cgstTaxBal", 0) or 0.0,
            "sgst":              obj.get("sgstTaxBal", 0) or 0.0,
            "cess":              obj.get("cessTaxBal", 0) or 0.0,
            "total_range_balance": obj.get("tot_rng_bal", 0) or 0.0,
        }

    def _parse_transaction(tr: dict) -> Dict[str, Any]:
        return {
            # ── Identity ──────────────────────────────────────────────────────
            "reference_number":  tr.get("ref_no"),
            "date":              tr.get("dt"),
            "return_period":     tr.get("ret_period"),
            "description":       tr.get("desc"),
            "transaction_type":  tr.get("tr_typ"),       # "Cr" or "Dr"

            # ── Transaction amounts (the movement for this entry) ─────────────
            "transaction_amount": {
                "igst": tr.get("igstTaxAmt", 0) or 0.0,
                "cgst": tr.get("cgstTaxAmt", 0) or 0.0,
                "sgst": tr.get("sgstTaxAmt", 0) or 0.0,
                "cess": tr.get("cessTaxAmt", 0) or 0.0,
                "total": tr.get("tot_tr_amt", 0) or 0.0,
            },

            # ── Running balance after this transaction ────────────────────────
            "balance_after": {
                "igst": tr.get("igstTaxBal", 0) or 0.0,
                "cgst": tr.get("cgstTaxBal", 0) or 0.0,
                "sgst": tr.get("sgstTaxBal", 0) or 0.0,
                "cess": tr.get("cessTaxBal", 0) or 0.0,
                "total_range_balance": tr.get("tot_rng_bal", 0) or 0.0,
            },
        }

    transactions = [_parse_transaction(tr) for tr in ledger.get("tr", []) or []]

    return {
        "success":   True,
        "status_cd": status_cd,
        "gstin":     ledger.get("gstin"),
        "from_date": ledger.get("fr_dt"),
        "to_date":   ledger.get("to_dt"),

        # Opening ITC balance at the start of the requested period
        "opening_balance": _balance_block(ledger.get("op_bal", {})),

        # Closing ITC balance at the end of the requested period
        "closing_balance": _balance_block(ledger.get("cl_bal", {})),

        # Chronological list of ITC credit/debit entries with running balance
        "transactions": transactions,

        # Provisional credit balance list (returned as empty list in most cases)
        "provisional_credit_balances": prov_crd.get("provCrdBal", []) or [],

        "raw": payload,
    }


def get_return_liability_ledger(gstin: str, year: str, month: str, from_date: str, to_date: str) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/ledgers/tax/{year}/{month}"

    headers = {
        "Authorization": token,
        "x-api-key":     API_KEY,
        "x-api-version": API_VERSION,
        "x-source":      "primary",
    }

    params = {
        "from": from_date,
        "to":   to_date,
    }

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
            "success":    False,
            "status_cd":  "0",
            "error_code": error_block.get("error_cd"),
            "message":    error_block.get("message"),
            "raw":        payload,
        }

    inner = outer_data.get("data", {})

    def _liability_block(obj: dict) -> Dict[str, float]:
        # Each tax-head liability block carries: tx, intr, pen, fee, oth, tot
        return {
            "tax":      obj.get("tx",   0) or 0.0,
            "interest": obj.get("intr", 0) or 0.0,
            "penalty":  obj.get("pen",  0) or 0.0,
            "fee":      obj.get("fee",  0) or 0.0,
            "other":    obj.get("oth",  0) or 0.0,
            "total":    obj.get("tot",  0) or 0.0,
        }

    def _balance_snapshot(obj: dict) -> Dict[str, Any]:
        # Used for op_bal / cl_bal and the per-transaction *bal running balance
        return {
            "igst":                _liability_block(obj.get("igstbal", {})),
            "cgst":                _liability_block(obj.get("cgstbal", {})),
            "sgst":                _liability_block(obj.get("sgstbal", {})),
            "cess":                _liability_block(obj.get("cessbal", {})),
            "total_range_balance": obj.get("tot_rng_bal", 0) or 0.0,
        }

    def _parse_transaction(tr: dict) -> Dict[str, Any]:
        return {
            # ── Identity ──────────────────────────────────────────────────────
            "reference_number":   tr.get("ref_no"),
            "date":               tr.get("dt"),
            "description":        tr.get("desc"),
            "transaction_type":   tr.get("tr_typ"),        # "Cr" or "Dr"
            "discharge_type":     tr.get("dschrg_typ") or None,  # "credit" / "" / None
            "total_transaction_amount": tr.get("tot_tr_amt", 0) or 0.0,
            "total_range_balance_after": tr.get("tot_rng_bal", 0) or 0.0,

            # ── Transaction amounts (the movement for this entry) ─────────────
            # Each tax head broken down by sub-head: tax/interest/penalty/fee/other/total
            "transaction_amount": {
                "igst": _liability_block(tr.get("igst", {})),
                "cgst": _liability_block(tr.get("cgst", {})),
                "sgst": _liability_block(tr.get("sgst", {})),
                "cess": _liability_block(tr.get("cess", {})),
            },

            # ── Running liability balance after this transaction ───────────────
            "balance_after": {
                "igst": _liability_block(tr.get("igstbal", {})),
                "cgst": _liability_block(tr.get("cgstbal", {})),
                "sgst": _liability_block(tr.get("sgstbal", {})),
                "cess": _liability_block(tr.get("cessbal", {})),
            },
        }

    transactions = [_parse_transaction(tr) for tr in inner.get("tr", []) or []]

    return {
        "success":   True,
        "status_cd": status_cd,
        "gstin":     inner.get("gstin"),
        "from_date": inner.get("fr_dt"),
        "to_date":   inner.get("to_dt"),

        # Closing liability balance at the end of the requested period
        # (no op_bal in the schema — only cl_bal is present for this ledger)
        "closing_balance": _balance_snapshot(inner.get("cl_bal", {})),

        # Chronological liability debit/credit entries with running balance
        "transactions": transactions,

        "raw": payload,
    }


get_cash_itc_balance = persist_service_result("get_cash_itc_balance")(get_cash_itc_balance)
get_cash_ledger = persist_service_result("get_cash_ledger")(get_cash_ledger)
get_itc_ledger = persist_service_result("get_itc_ledger")(get_itc_ledger)
get_return_liability_ledger = persist_service_result("get_return_liability_ledger")(get_return_liability_ledger)


