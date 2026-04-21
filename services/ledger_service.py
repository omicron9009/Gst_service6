
# Completely Written 


import requests
from typing import Dict, Any, Optional
import config
from session_storage import get_session

# Persistence helpers
from database.core.database import get_sync_db
from database.models.client import Client
from database.services.ledger.models import LedgerBalance, LedgerCash, LedgerItc, LedgerLiability


def _get_or_create_client(gstin: str, session) -> Client:
    client = session.query(Client).filter(Client.gstin == gstin).first()
    if not client:
        client = Client(gstin=gstin, username="", is_active=True)
        session.add(client)
        session.flush()
    return client


def get_cash_itc_balance(gstin: str, year: str, month: str) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{config.BASE_URL}/gst/compliance/tax-payer/ledgers/bal/{year}/{month}"

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

    result = {
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

    # ─────────────────────────────────────────────────────────────────────────
    # Persist to DB
    # ─────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = _get_or_create_client(gstin, db_session)

            cash_bal = result.get("cash_balance", {})
            itc_bal = result.get("itc_balance", {})
            itc_blocked = result.get("itc_blocked_balance", {})

            payload_for_db = {
                "year": year,
                "month": month,
                "cash_igst_tax": cash_bal.get("igst", {}).get("tax"),
                "cash_igst_interest": cash_bal.get("igst", {}).get("interest"),
                "cash_igst_penalty": cash_bal.get("igst", {}).get("penalty"),
                "cash_igst_fee": cash_bal.get("igst", {}).get("fee"),
                "cash_igst_other": cash_bal.get("igst", {}).get("other"),
                "cash_igst_total": cash_bal.get("igst", {}).get("total"),
                "cash_cgst_total": cash_bal.get("cgst", {}).get("total"),
                "cash_sgst_total": cash_bal.get("sgst", {}).get("total"),
                "cash_cess_total": cash_bal.get("cess", {}).get("total"),
                "itc_igst": itc_bal.get("igst"),
                "itc_cgst": itc_bal.get("cgst"),
                "itc_sgst": itc_bal.get("sgst"),
                "itc_cess": itc_bal.get("cess"),
                "itc_blocked_igst": itc_blocked.get("igst"),
                "itc_blocked_cgst": itc_blocked.get("cgst"),
                "itc_blocked_sgst": itc_blocked.get("sgst"),
                "itc_blocked_cess": itc_blocked.get("cess"),
                "status_cd": status_cd,
                "upstream_status_code": response.status_code,
            }

            existing = db_session.query(LedgerBalance).filter(
                LedgerBalance.client_id == client.id,
                LedgerBalance.year == year,
                LedgerBalance.month == month,
            ).first()

            if existing:
                for field, value in payload_for_db.items():
                    setattr(existing, field, value)
            else:
                record = LedgerBalance(client_id=client.id, **payload_for_db)
                db_session.add(record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving ledger balance: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session for ledger balance: {e}")

    return result



def get_cash_ledger(gstin: str, from_date: str, to_date: str) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{config.BASE_URL}/gst/compliance/tax-payer/ledgers/cash"

    headers = {
        "Authorization": token,
        "x-api-key":     config.API_KEY,
        "x-api-version": config.API_VERSION,
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

    def _parse_transaction(tr: dict) -> Dict[str, Any]:
        # Cash ledger transactions often contain tax-head blocks; expose a single amount for UI and keep per-head totals
        heads = {
            "igst": _ledger_balance(tr.get("igst", {})),
            "cgst": _ledger_balance(tr.get("cgst", {})),
            "sgst": _ledger_balance(tr.get("sgst", {})),
            "cess": _ledger_balance(tr.get("cess", {})),
        }

        # Prefer explicit total if present; otherwise sum tax sub-heads
        amount = tr.get("tot_tr_amt")
        if amount is None:
            amount = tr.get("tot")
        if amount is None:
            amount = sum((heads[h].get("total") or 0) for h in heads)

        return {
            "ref_no": tr.get("ref_no"),
            "dt": tr.get("dt"),
            "ret_period": tr.get("ret_period"),
            "desc": tr.get("desc"),
            "tr_typ": tr.get("tr_typ"),
            "dschrg_typ": tr.get("dschrg_typ"),
            "amount": amount or 0.0,
            "heads": heads,
            "balance_after": {
                "igst": _ledger_balance(tr.get("igstbal", {})),
                "cgst": _ledger_balance(tr.get("cgstbal", {})),
                "sgst": _ledger_balance(tr.get("sgstbal", {})),
                "cess": _ledger_balance(tr.get("cessbal", {})),
                "total_range_balance": tr.get("tot_rng_bal", 0) or 0.0,
            },
        }

    # ── Transactions ──────────────────────────────────────────────────────────
    # tr is an array of transaction entries for the period.
    # The API returns [] when no transactions exist in the date range.
    transactions = [_parse_transaction(tr) for tr in inner.get("tr", []) or []]

    opening = _parse_balance_block(inner.get("op_bal", {}))
    closing = _parse_balance_block(inner.get("cl_bal", {}))

    # Add opening/closing snapshots as informational rows for the UI
    if opening:
        transactions.insert(0, {
            "ref_no": "OPEN",
            "dt": inner.get("fr_dt"),
            "desc": "Opening Balance",
            "tr_typ": "OPEN",
            "amount": opening.get("total_range_balance", 0),
        })
    if closing:
        transactions.append({
            "ref_no": "CLOSE",
            "dt": inner.get("to_dt"),
            "desc": "Closing Balance",
            "tr_typ": "CLOSE",
            "amount": closing.get("total_range_balance", 0),
        })

    result = {
        "success":   True,
        "status_cd": status_cd,
        "gstin":     inner.get("gstin"),
        "from_date": inner.get("fr_dt"),
        "to_date":   inner.get("to_dt"),

        # Opening balance at the start of the requested period
        "opening_balance": opening,

        # Closing balance at the end of the requested period
        "closing_balance": closing,

        # Individual transactions within the period (empty list if none)
        "transactions": transactions,

        "raw": payload,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # Persist to DB
    # ─────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = _get_or_create_client(gstin, db_session)

            existing = db_session.query(LedgerCash).filter(
                LedgerCash.client_id == client.id,
                LedgerCash.from_date == from_date,
                LedgerCash.to_date == to_date,
            ).first()

            payload_for_db = {
                "from_date": from_date,
                "to_date": to_date,
                "opening_balance": opening,
                "closing_balance": closing,
                "transactions": transactions,
                "status_cd": status_cd,
                "upstream_status_code": response.status_code,
            }

            if existing:
                for field, value in payload_for_db.items():
                    setattr(existing, field, value)
            else:
                record = LedgerCash(client_id=client.id, **payload_for_db)
                db_session.add(record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving cash ledger: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session for cash ledger: {e}")

    return result

def get_itc_ledger(gstin: str, from_date: str, to_date: str) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{config.BASE_URL}/gst/compliance/tax-payer/ledgers/itc"

    headers = {
        "Authorization": token,
        "x-api-key":     config.API_KEY,
        "x-api-version": config.API_VERSION,
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
            "ref_no":      tr.get("ref_no"),
            "dt":          tr.get("dt"),
            "ret_period":  tr.get("ret_period"),
            "desc":        tr.get("desc"),
            "tr_typ":      tr.get("tr_typ"),       # "Cr" or "Dr"

            # ── Transaction amounts (movement) ──────────────────────────────
            "igst_amt":   tr.get("igstTaxAmt", 0) or 0.0,
            "cgst_amt":   tr.get("cgstTaxAmt", 0) or 0.0,
            "sgst_amt":   tr.get("sgstTaxAmt", 0) or 0.0,
            "cess_amt":   tr.get("cessTaxAmt", 0) or 0.0,
            "total_amount": tr.get("tot_tr_amt", 0) or 0.0,

            # ── Running balance after this transaction ───────────────────────
            "igst_bal":   tr.get("igstTaxBal", 0) or 0.0,
            "cgst_bal":   tr.get("cgstTaxBal", 0) or 0.0,
            "sgst_bal":   tr.get("sgstTaxBal", 0) or 0.0,
            "cess_bal":   tr.get("cessTaxBal", 0) or 0.0,
            "total_range_balance": tr.get("tot_rng_bal", 0) or 0.0,
        }

    transactions = [_parse_transaction(tr) for tr in ledger.get("tr", []) or []]

    opening = _balance_block(ledger.get("op_bal", {}))
    closing = _balance_block(ledger.get("cl_bal", {}))

    # Inject opening / closing snapshots into transaction stream for UI visibility
    if opening:
        transactions.insert(0, {
            "ref_no": "OPEN",
            "dt": ledger.get("fr_dt"),
            "desc": "Opening Balance",
            "tr_typ": "OPEN",
            "total_amount": opening.get("total_range_balance", 0),
            "igst_bal": opening.get("igst"),
            "cgst_bal": opening.get("cgst"),
            "sgst_bal": opening.get("sgst"),
            "cess_bal": opening.get("cess"),
            "total_range_balance": opening.get("total_range_balance", 0),
        })
    if closing:
        transactions.append({
            "ref_no": "CLOSE",
            "dt": ledger.get("to_dt"),
            "desc": "Closing Balance",
            "tr_typ": "CLOSE",
            "total_amount": closing.get("total_range_balance", 0),
            "igst_bal": closing.get("igst"),
            "cgst_bal": closing.get("cgst"),
            "sgst_bal": closing.get("sgst"),
            "cess_bal": closing.get("cess"),
            "total_range_balance": closing.get("total_range_balance", 0),
        })

    result = {
        "success":   True,
        "status_cd": status_cd,
        "gstin":     ledger.get("gstin"),
        "from_date": ledger.get("fr_dt"),
        "to_date":   ledger.get("to_dt"),

        # Opening ITC balance at the start of the requested period
        "opening_balance": opening,

        # Closing ITC balance at the end of the requested period
        "closing_balance": closing,

        # Chronological list of ITC credit/debit entries with running balance
        "transactions": transactions,

        # Provisional credit balance list (returned as empty list in most cases)
        "provisional_credit_balances": prov_crd.get("provCrdBal", []) or [],

        "raw": payload,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # Persist to DB
    # ─────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = _get_or_create_client(gstin, db_session)

            payload_for_db = {
                "from_date": from_date,
                "to_date": to_date,
                "opening_igst": opening.get("igst"),
                "opening_cgst": opening.get("cgst"),
                "opening_sgst": opening.get("sgst"),
                "opening_cess": opening.get("cess"),
                "opening_total_range_balance": opening.get("total_range_balance"),
                "closing_igst": closing.get("igst"),
                "closing_cgst": closing.get("cgst"),
                "closing_sgst": closing.get("sgst"),
                "closing_cess": closing.get("cess"),
                "closing_total_range_balance": closing.get("total_range_balance"),
                "transactions": transactions,
                "provisional_credit_balances": result.get("provisional_credit_balances"),
                "status_cd": status_cd,
                "upstream_status_code": response.status_code,
            }

            existing = db_session.query(LedgerItc).filter(
                LedgerItc.client_id == client.id,
                LedgerItc.from_date == from_date,
                LedgerItc.to_date == to_date,
            ).first()

            if existing:
                for field, value in payload_for_db.items():
                    setattr(existing, field, value)
            else:
                record = LedgerItc(client_id=client.id, **payload_for_db)
                db_session.add(record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving ITC ledger: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session for ITC ledger: {e}")

    return result


def get_return_liability_ledger(gstin: str, year: str, month: str, from_date: str, to_date: str) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{config.BASE_URL}/gst/compliance/tax-payer/ledgers/tax/{year}/{month}"

    headers = {
        "Authorization": token,
        "x-api-key":     config.API_KEY,
        "x-api-version": config.API_VERSION,
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
        tx_amt = {
            "igst": _liability_block(tr.get("igst", {})),
            "cgst": _liability_block(tr.get("cgst", {})),
            "sgst": _liability_block(tr.get("sgst", {})),
            "cess": _liability_block(tr.get("cess", {})),
        }

        bal_after = {
            "igst": _liability_block(tr.get("igstbal", {})),
            "cgst": _liability_block(tr.get("cgstbal", {})),
            "sgst": _liability_block(tr.get("sgstbal", {})),
            "cess": _liability_block(tr.get("cessbal", {})),
            "total_range_balance": tr.get("tot_rng_bal", 0) or 0.0,
        }

        return {
            # ── Identity ──────────────────────────────────────────────────────
            "ref_no":   tr.get("ref_no"),
            "dt":       tr.get("dt"),
            "desc":     tr.get("desc"),
            "tr_typ":   tr.get("tr_typ"),        # "Cr" or "Dr"
            "dschrg_typ": tr.get("dschrg_typ") or None,  # "credit" / "" / None

            # Totals
            "tot_tr_amt": tr.get("tot_tr_amt", 0) or 0.0,
            "tot_rng_bal": tr.get("tot_rng_bal", 0) or 0.0,

            # Per-head totals for table friendliness
            "igst_amt": tx_amt["igst"].get("total"),
            "cgst_amt": tx_amt["cgst"].get("total"),
            "sgst_amt": tx_amt["sgst"].get("total"),
            "cess_amt": tx_amt["cess"].get("total"),

            # Running balance per head (totals)
            "igst_bal": bal_after["igst"].get("total"),
            "cgst_bal": bal_after["cgst"].get("total"),
            "sgst_bal": bal_after["sgst"].get("total"),
            "cess_bal": bal_after["cess"].get("total"),
            "total_range_balance": bal_after.get("total_range_balance", 0),

            # Full detail retained
            "transaction_amount": tx_amt,
            "balance_after": bal_after,
        }

    transactions = [_parse_transaction(tr) for tr in inner.get("tr", []) or []]

    closing = _balance_snapshot(inner.get("cl_bal", {}))

    if closing:
        transactions.append({
            "ref_no": "CLOSE",
            "dt": inner.get("to_dt"),
            "desc": "Closing Balance",
            "tr_typ": "CLOSE",
            "tot_tr_amt": closing.get("total_range_balance", 0),
            "tot_rng_bal": closing.get("total_range_balance", 0),
            "igst_bal": closing.get("igst", {}).get("total"),
            "cgst_bal": closing.get("cgst", {}).get("total"),
            "sgst_bal": closing.get("sgst", {}).get("total"),
            "cess_bal": closing.get("cess", {}).get("total"),
            "total_range_balance": closing.get("total_range_balance", 0),
            "balance_after": closing,
        })

    result = {
        "success":   True,
        "status_cd": status_cd,
        "gstin":     inner.get("gstin"),
        "from_date": inner.get("fr_dt"),
        "to_date":   inner.get("to_dt"),

        # Closing liability balance at the end of the requested period
        # (no op_bal in the schema — only cl_bal is present for this ledger)
        "closing_balance": closing,

        # Chronological liability debit/credit entries with running balance
        "transactions": transactions,

        "raw": payload,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # Persist to DB
    # ─────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = _get_or_create_client(gstin, db_session)

            payload_for_db = {
                "year": year,
                "month": month,
                "from_date": from_date,
                "to_date": to_date,
                "closing_balance": closing,
                "transactions": transactions,
                "status_cd": status_cd,
                "upstream_status_code": response.status_code,
            }

            existing = db_session.query(LedgerLiability).filter(
                LedgerLiability.client_id == client.id,
                LedgerLiability.year == year,
                LedgerLiability.month == month,
                LedgerLiability.from_date == from_date,
                LedgerLiability.to_date == to_date,
            ).first()

            if existing:
                for field, value in payload_for_db.items():
                    setattr(existing, field, value)
            else:
                record = LedgerLiability(client_id=client.id, **payload_for_db)
                db_session.add(record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving liability ledger: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session for liability ledger: {e}")

    return result


