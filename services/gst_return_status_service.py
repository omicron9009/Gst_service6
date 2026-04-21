# ─────────────────────────────────────────────────────────────────────────────
# STATUS CODES ACROSS ALL 200-OK VARIANTS
#
# outer status_cd (data.status_cd):  "1" = GST processed OK, "0" = GST error
# inner status_cd (data.data.status_cd):
#   "P"   → Processed successfully (no errors)
#   "PE"  → Processed with errors  (error_report will be present)
#   "ER"  → Error (entire submission rejected, error_report at top level)
#   "REC" → Reset request received / in queue
#
# action:   "SAVE" | "RESET"
# form_typ: "R1" (GSTR-1) | "R3B" (GSTR-3B) | "R9" (GSTR-9)
# ─────────────────────────────────────────────────────────────────────────────
import requests
from typing import Dict, Any, Optional
import config
from session_storage import get_session

# Persistence
from database.core.database import get_sync_db
from database.models.client import Client
from database.services.gst_return_status.models import GstReturnStatus


def _get_or_create_client(gstin: str, session) -> Client:
    client = session.query(Client).filter(Client.gstin == gstin).first()
    if not client:
        client = Client(gstin=gstin, username="", is_active=True)
        session.add(client)
        session.flush()
    return client


def _upsert_return_status(
    db_session,
    *,
    client_id: int,
    year: str,
    month: str,
    reference_id: str,
    status_cd: Optional[str],
    upstream_status_code: int,
    form_type: Optional[str] = None,
    form_type_label: Optional[str] = None,
    action: Optional[str] = None,
    processing_status: Optional[str] = None,
    processing_status_label: Optional[str] = None,
    has_errors: Optional[bool] = None,
    error_report: Optional[dict[str, Any]] = None,
) -> None:
    existing = (
        db_session.query(GstReturnStatus)
        .filter(
            GstReturnStatus.client_id == client_id,
            GstReturnStatus.year == year,
            GstReturnStatus.month == month,
            GstReturnStatus.reference_id == reference_id,
        )
        .first()
    )

    values = {
        "form_type": form_type,
        "form_type_label": form_type_label,
        "action": action,
        "processing_status": processing_status,
        "processing_status_label": processing_status_label,
        "has_errors": has_errors,
        "error_report": error_report,
        "status_cd": status_cd,
        "upstream_status_code": upstream_status_code,
    }

    if existing:
        for field, value in values.items():
            setattr(existing, field, value)
    else:
        db_session.add(
            GstReturnStatus(
                client_id=client_id,
                year=year,
                month=month,
                reference_id=reference_id,
                **values,
            )
        )


def get_gst_return_status(gstin: str, year: str, month: str, reference_id: str) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{config.BASE_URL}/gst/compliance/tax-payer/gstrs/{year}/{month}/status"

    headers = {
        "Authorization": token,
        "x-api-key":     config.API_KEY,
        "x-api-version": config.API_VERSION,
        "x-source":      "primary",
    }

    params = {"reference_id": reference_id}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        payload = response.json()
    except Exception as e:
        return {"success": False, "message": "Failed to contact GST API", "error": str(e)}

    outer_data = payload.get("data", {})
    status_cd  = str(outer_data.get("status_cd", ""))

    # ── Outer status_cd = "0" → GST-level transport/auth error ───────────────
    if status_cd == "0":
        error_block = outer_data.get("error", {})
        result = {
            "success":    False,
            "status_cd":  "0",
            "error_code": error_block.get("error_cd"),
            "message":    error_block.get("message"),
            "raw":        payload,
        }

        # Upsert by period + reference id to avoid duplicate status rows.
        try:
            db_session = get_sync_db()
            try:
                client = _get_or_create_client(gstin, db_session)
                _upsert_return_status(
                    db_session,
                    client_id=client.id,
                    year=year,
                    month=month,
                    reference_id=reference_id,
                    status_cd="0",
                    upstream_status_code=response.status_code,
                    error_report={
                        "error_code": result.get("error_code"),
                        "error_message": result.get("message"),
                    },
                    has_errors=True,
                )
                db_session.commit()
            except Exception as db_error:
                db_session.rollback()
                print(f"Database error saving GST return status error: {db_error}")
            finally:
                db_session.close()
        except Exception as e:
            print(f"Failed to get database session for GST return status error: {e}")

        return result

    inner      = outer_data.get("data", {})
    action     = inner.get("action")          # "SAVE" | "RESET"
    form_typ   = inner.get("form_typ")        # "R1" | "R3B" | "R9"
    inner_status = inner.get("status_cd")     # "P" | "PE" | "ER" | "REC"
    error_report = inner.get("error_report")  # present on PE / ER, absent on P / REC

    # ── Human-readable labels ─────────────────────────────────────────────────
    FORM_LABELS = {"R1": "GSTR-1", "R3B": "GSTR-3B", "R9": "GSTR-9"}
    STATUS_LABELS = {
        "P":   "Processed",
        "PE":  "Processed with errors",
        "ER":  "Error — submission rejected",
        "REC": "Reset request received",
    }

    # ── Helpers for error_report section parsers ──────────────────────────────
    def _itm(itm: dict) -> Dict[str, Any]:
        det = itm.get("itm_det", itm)   # b2b/cdnr wrap in itm_det, others are flat
        return {
            "item_number":     itm.get("num"),
            "tax_rate":        det.get("rt"),
            "taxable_value":   det.get("txval"),
            "igst":            det.get("iamt"),
            "cgst":            det.get("camt"),
            "sgst":            det.get("samt"),
            "cess":            det.get("csamt"),
            "advance_amount":  det.get("ad_amt"),  # txpd / at sections
        }

    def _parse_b2b_errors(entries: list) -> list:
        # [{ctin, error_cd, error_msg, inv:[{inum,idt,inv_typ,pos,rchrg,val,etin,itms}]}]
        result = []
        for entry in (entries or []):
            invoices = []
            for inv in (entry.get("inv") or []):
                invoices.append({
                    "invoice_number": inv.get("inum"),
                    "invoice_date":   inv.get("idt"),
                    "invoice_type":   inv.get("inv_typ"),
                    "pos":            inv.get("pos"),
                    "reverse_charge": inv.get("rchrg"),
                    "etin":           inv.get("etin"),
                    "value":          inv.get("val"),
                    "items":          [_itm(i) for i in (inv.get("itms") or [])],
                })
            result.append({
                "counterparty_gstin": entry.get("ctin"),
                "error_code":         entry.get("error_cd"),
                "error_message":      entry.get("error_msg"),
                "invoices":           invoices,
            })
        return result

    def _parse_b2cl_errors(entries: list) -> list:
        # [{pos, error_cd, error_msg, inv:[{inum,idt,etin,val,itms}]}]
        result = []
        for entry in (entries or []):
            invoices = []
            for inv in (entry.get("inv") or []):
                invoices.append({
                    "invoice_number": inv.get("inum"),
                    "invoice_date":   inv.get("idt"),
                    "etin":           inv.get("etin"),
                    "value":          inv.get("val"),
                    "items":          [_itm(i) for i in (inv.get("itms") or [])],
                })
            result.append({
                "pos":           entry.get("pos"),
                "error_code":    entry.get("error_cd"),
                "error_message": entry.get("error_msg"),
                "invoices":      invoices,
            })
        return result

    def _parse_b2cs_errors(entries: list) -> list:
        # flat rows — no nested inv array
        result = []
        for entry in (entries or []):
            result.append({
                "pos":            entry.get("pos"),
                "supply_type":    entry.get("sply_ty"),
                "type":           entry.get("typ"),
                "etin":           entry.get("etin"),
                "tax_rate":       entry.get("rt"),
                "taxable_value":  entry.get("txval"),
                "igst":           entry.get("iamt"),
                "cess":           entry.get("csamt"),
                "error_code":     entry.get("error_cd"),
                "error_message":  entry.get("error_msg"),
            })
        return result

    def _parse_cdnr_errors(entries: list) -> list:
        # [{ctin, error_cd, error_msg, nt:[{inum,idt,nt_num,nt_dt,ntty,rsn,p_gst,val,itms}]}]
        result = []
        for entry in (entries or []):
            notes = []
            for nt in (entry.get("nt") or []):
                notes.append({
                    "invoice_number":  nt.get("inum"),
                    "invoice_date":    nt.get("idt"),
                    "note_number":     nt.get("nt_num"),
                    "note_date":       nt.get("nt_dt"),
                    "note_type":       nt.get("ntty"),     # "C" (credit) / "D" (debit)
                    "reason":          nt.get("rsn"),
                    "pre_gst":         nt.get("p_gst"),
                    "value":           nt.get("val"),
                    "items":           [_itm(i) for i in (nt.get("itms") or [])],
                })
            result.append({
                "counterparty_gstin": entry.get("ctin"),
                "error_code":         entry.get("error_cd"),
                "error_message":      entry.get("error_msg"),
                "notes":              notes,
            })
        return result

    def _parse_cdnur_errors(entries: list) -> list:
        # flat note rows (no ctin grouping)
        result = []
        for entry in (entries or []):
            result.append({
                "invoice_number": entry.get("inum"),
                "invoice_date":   entry.get("idt"),
                "note_number":    entry.get("nt_num"),
                "note_date":      entry.get("nt_dt"),
                "note_type":      entry.get("ntty"),
                "type":           entry.get("typ"),
                "reason":         entry.get("rsn"),
                "pre_gst":        entry.get("p_gst"),
                "value":          entry.get("val"),
                "items":          [_itm(i) for i in (entry.get("itms") or [])],
                "error_code":     entry.get("error_cd"),
                "error_message":  entry.get("error_msg"),
            })
        return result

    def _parse_exp_errors(entries: list) -> list:
        # [{exp_typ, error_cd, error_msg, inv:[{inum,idt,sbnum,sbdt,sbpcode,val,itms}]}]
        result = []
        for entry in (entries or []):
            invoices = []
            for inv in (entry.get("inv") or []):
                invoices.append({
                    "invoice_number":     inv.get("inum"),
                    "invoice_date":       inv.get("idt"),
                    "shipping_bill_num":  inv.get("sbnum"),
                    "shipping_bill_date": inv.get("sbdt"),
                    "port_code":          inv.get("sbpcode"),
                    "value":              inv.get("val"),
                    "items":              [_itm(i) for i in (inv.get("itms") or [])],
                })
            result.append({
                "export_type":   entry.get("exp_typ"),   # "WPAY" | "WOPAY"
                "error_code":    entry.get("error_cd"),
                "error_message": entry.get("error_msg"),
                "invoices":      invoices,
            })
        return result

    def _parse_at_txpd_errors(entries: list) -> list:
        # advance tax rows [{pos, sply_ty, error_cd, error_msg, itms}]
        result = []
        for entry in (entries or []):
            result.append({
                "pos":           entry.get("pos"),
                "supply_type":   entry.get("sply_ty"),
                "error_code":    entry.get("error_cd"),
                "error_message": entry.get("error_msg"),
                "items":         [_itm(i) for i in (entry.get("itms") or [])],
            })
        return result

    def _parse_hsn_errors(hsn_block) -> Dict[str, Any]:
        # hsn can be a dict with {data:[], error_cd, error_msg}
        # OR a list of {chksum, data:[], error_cd, error_msg} entries
        if isinstance(hsn_block, dict):
            return {
                "error_code":    hsn_block.get("error_cd"),
                "error_message": hsn_block.get("error_msg"),
                "items": [
                    {
                        "hsn_sac":     row.get("hsn_sc"),
                        "description": row.get("desc"),
                        "uqc":         row.get("uqc"),
                        "quantity":    row.get("qty"),
                        "num":         row.get("num"),
                        "tax_rate":    row.get("rt"),
                        "taxable_value": row.get("txval"),
                        "igst":        row.get("iamt"),
                        "cgst":        row.get("camt"),
                        "sgst":        row.get("samt"),
                        "cess":        row.get("csamt"),
                        "value":       row.get("val"),
                    }
                    for row in (hsn_block.get("data") or [])
                ],
            }
        if isinstance(hsn_block, list):
            groups = []
            for grp in hsn_block:
                groups.append({
                    "checksum":      grp.get("chksum"),
                    "error_code":    grp.get("error_cd"),
                    "error_message": grp.get("error_msg"),
                    "items": [
                        {
                            "hsn_sac":       row.get("hsn_sc"),
                            "description":   row.get("desc"),
                            "uqc":           row.get("uqc"),
                            "quantity":      row.get("qty"),
                            "num":           row.get("num"),
                            "tax_rate":      row.get("rt"),
                            "taxable_value": row.get("txval"),
                            "igst":          row.get("iamt"),
                            "cgst":          row.get("camt"),
                            "sgst":          row.get("samt"),
                            "cess":          row.get("csamt"),
                        }
                        for row in (grp.get("data") or [])
                    ],
                })
            return {"groups": groups}
        return {}

    def _parse_nil_errors(nil_block: dict) -> Dict[str, Any]:
        return {
            "error_code":    nil_block.get("error_cd"),
            "error_message": nil_block.get("error_msg"),
            "supplies": [
                {
                    "supply_type":  row.get("sply_ty"),
                    "nil_amount":   row.get("nil_amt"),
                    "exempt_amount": row.get("expt_amt"),
                    "non_gst_amount": row.get("ngsup_amt"),
                }
                for row in (nil_block.get("inv") or [])
            ],
        }

    def _parse_doc_issue_errors(doc_block: dict) -> Dict[str, Any]:
        return {
            "error_code":    doc_block.get("error_cd"),
            "error_message": doc_block.get("error_msg"),
            "document_details": [
                {
                    "doc_num": dd.get("doc_num"),
                    "docs": [
                        {
                            "serial_number": d.get("num"),
                            "from":          d.get("from"),
                            "to":            d.get("to"),
                            "total_issued":  d.get("totnum"),
                            "cancelled":     d.get("cancel"),
                            "net_issued":    d.get("net_issue"),
                        }
                        for d in (dd.get("docs") or [])
                    ],
                }
                for dd in (doc_block.get("doc_det") or [])
            ],
        }

    def _parse_table17_errors(t17_block: dict) -> Dict[str, Any]:
        return {
            "items": [
                {
                    "hsn_sac":          row.get("hsn_sc"),
                    "tax_rate":         row.get("rt"),
                    "taxable_value":    row.get("txval"),
                    "igst":             row.get("iamt"),
                    "cgst":             row.get("camt"),
                    "sgst":             row.get("samt"),
                    "cess":             row.get("csamt"),
                    "is_concessional":  row.get("isconcesstional"),
                    "error_code":       row.get("error_cd"),
                    "error_message":    row.get("error_msg"),
                }
                for row in (t17_block.get("items") or [])
            ]
        }

    def _parse_error_report(er) -> Dict[str, Any]:
        if not er:
            return {}
        # Top-level flat error (e.g. RET191106, RET191251) — no section keys
        if "error_cd" in er and len(er) <= 2:
            return {
                "error_code":    er.get("error_cd"),
                "error_message": er.get("error_msg"),
            }
        # Section-level errors
        parsed = {}
        if er.get("b2b"):
            parsed["b2b"] = _parse_b2b_errors(er["b2b"])
        if er.get("b2cl"):
            parsed["b2cl"] = _parse_b2cl_errors(er["b2cl"])
        if er.get("b2cs"):
            parsed["b2cs"] = _parse_b2cs_errors(er["b2cs"])
        if er.get("cdnr"):
            parsed["cdnr"] = _parse_cdnr_errors(er["cdnr"])
        if er.get("cdnur"):
            parsed["cdnur"] = _parse_cdnur_errors(er["cdnur"])
        if er.get("exp"):
            parsed["exp"] = _parse_exp_errors(er["exp"])
        if er.get("at"):
            parsed["at"] = _parse_at_txpd_errors(er["at"])
        if er.get("txpd"):
            parsed["txpd"] = _parse_at_txpd_errors(er["txpd"])
        if er.get("hsn") is not None:
            parsed["hsn"] = _parse_hsn_errors(er["hsn"])
        if er.get("nil"):
            parsed["nil"] = _parse_nil_errors(er["nil"])
        if er.get("doc_issue"):
            parsed["doc_issue"] = _parse_doc_issue_errors(er["doc_issue"])
        if er.get("table17"):
            parsed["table17"] = _parse_table17_errors(er["table17"])
        # Carry top-level error_cd if present alongside section errors
        if er.get("error_cd"):
            parsed["error_code"]    = er.get("error_cd")
            parsed["error_message"] = er.get("error_msg")
        return parsed

    result = {
        "success":        True,
        "status_cd":      status_cd,

        # ── What was submitted ────────────────────────────────────────────────
        "form_type":      form_typ,                          # "R1" | "R3B" | "R9"
        "form_type_label": FORM_LABELS.get(form_typ, form_typ),
        "action":         action,                            # "SAVE" | "RESET"

        # ── Processing outcome ────────────────────────────────────────────────
        # "P"   → clean, no errors
        # "PE"  → partial errors, some records rejected
        # "ER"  → full rejection, check error_report
        # "REC" → reset queued
        "processing_status":       inner_status,
        "processing_status_label": STATUS_LABELS.get(inner_status, inner_status),
        "has_errors":              inner_status in ("PE", "ER"),

        # ── Parsed error detail (None when status is "P" or "REC") ───────────
        # Sections present depend on which GSTR sections had issues:
        #   b2b, b2cl, b2cs, cdnr, cdnur, exp, at, txpd, hsn, nil,
        #   doc_issue (R1 only), table17 (R9 only),
        #   or a flat error_code/error_message for whole-form rejections
        "error_report": _parse_error_report(error_report) if error_report else None,

        "raw": payload,
    }

    # Upsert by period + reference id so polling updates existing row.
    try:
        db_session = get_sync_db()
        try:
            client = _get_or_create_client(gstin, db_session)
            _upsert_return_status(
                db_session,
                client_id=client.id,
                year=year,
                month=month,
                reference_id=reference_id,
                status_cd=status_cd,
                upstream_status_code=response.status_code,
                form_type=result.get("form_type"),
                form_type_label=result.get("form_type_label"),
                action=result.get("action"),
                processing_status=result.get("processing_status"),
                processing_status_label=result.get("processing_status_label"),
                has_errors=result.get("has_errors"),
                error_report=result.get("error_report"),
            )
            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving GST return status: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session for GST return status: {e}")

    return result


