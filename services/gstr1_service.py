# gstr1_service.py
# --------------- not available --------------
                    #ata
                    #b2ba
                    #b2cla
                    # cdnra
                    # cdnura
                    # expa

                    # txpa 
                    # ecom 
                    # ecoma 
                    # supeco
                    # supecoa
#------------------ -------------------------

# funtions in gstr 1 service : 
                # at 
                # b2b 
                # gstr1 summary 
                # b2csa
                # b2cs
                # cdnr
                # issued docs
                # hsn summary
                # nill rated 
                # b2cl 
                # cdnur 
                # exp
                # txp 

# ---------to do -------------
#       gst return status
#       return status 



import requests
from typing import Dict, Any, Optional

from config import BASE_URL, API_KEY, API_VERSION

# BUG FIX: Single consistent import of get_session from the flat module (not services.session_storage_manager)
from session_storage import get_session

# BUG FIX: Import from flat module names, not 'schemas.gstr1' / 'parsers.gstr1_parser'
from schemas.gstr1 import (
    Gstr1AdvanceTaxResponse,
    Gstr1RequestInfo,
)
from parsers.gstr1_parser import parse_gstr1_advance_tax

# Database imports for persistence
from database.core.database import get_sync_db
from database.models.client import Client
from database.services.gstr1.models import (
    Gstr1B2B,
    Gstr1Summary,
    Gstr1B2CSA,
    Gstr1B2CS,
    Gstr1CDNR,
    Gstr1DocIssue,
    Gstr1HSN,
    Gstr1Nil,
    Gstr1B2CL,
    Gstr1CDNUR,
    Gstr1EXP,
    Gstr1TXP,
    Gstr1AdvanceTax,
)


# ─────────────────────────────────────────────────────────────────────────────
# Database Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def get_or_create_client(gstin: str, session) -> Client:
    """Get or create a Client record by GSTIN."""
    client = session.query(Client).filter(Client.gstin == gstin).first()
    if not client:
        client = Client(gstin=gstin, username="", is_active=True)
        session.add(client)
        session.flush()  # Flush to get the ID without committing
    return client


# ---------------------------------------------------------------------------
# GSTR-1 Advance Tax (AT)
# ---------------------------------------------------------------------------

def get_gstr1_advance_tax(gstin: str, year: str, month: str) -> Gstr1AdvanceTaxResponse:
    """
    Fetch GSTR1 Advance Tax (AT).
    Always returns a Gstr1AdvanceTaxResponse model.
    """

    session = get_session(gstin)

    if not session:
        return Gstr1AdvanceTaxResponse(
            success=False,
            request=Gstr1RequestInfo(
                gstin=gstin,
                year=year,
                month=month,
                endpoint="GSTR-1 Advance Tax",
            ),
            upstream_status_code=0,
            data={"message": "GST session not found. Verify OTP first."},
        )

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-1/at/{year}/{month}"

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
        return Gstr1AdvanceTaxResponse(
            success=False,
            request=Gstr1RequestInfo(
                gstin=gstin,
                year=year,
                month=month,
                endpoint="GSTR-1 Advance Tax",
            ),
            upstream_status_code=0,
            data={"error": str(e)},
        )

    parsed_data = parse_gstr1_advance_tax(payload)

    # ─────────────────────────────────────────────────────────────────────────────
    # PERSIST TO DATABASE
    # ─────────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = get_or_create_client(gstin, db_session)

            # Convert parsed records to dicts for storage
            records = [entry.model_dump() for entry in parsed_data]

            # Check if record already exists
            existing = db_session.query(Gstr1AdvanceTax).filter(
                Gstr1AdvanceTax.client_id == client.id,
                Gstr1AdvanceTax.year == year,
                Gstr1AdvanceTax.month == month,
            ).first()

            if existing:
                # Update existing record
                existing.records = records
                existing.upstream_status_code = response.status_code
            else:
                # Create new record
                at_record = Gstr1AdvanceTax(
                    client_id=client.id,
                    year=year,
                    month=month,
                    records=records,
                    upstream_status_code=response.status_code,
                )
                db_session.add(at_record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving GSTR1 Advance Tax: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session: {e}")

    return Gstr1AdvanceTaxResponse(
        success=True,
        request=Gstr1RequestInfo(
            gstin=gstin,
            year=year,
            month=month,
            endpoint="GSTR-1 Advance Tax",
        ),
        upstream_status_code=response.status_code,
        data={
            "raw": payload,
            "parsed": [entry.model_dump() for entry in parsed_data],
        },
    )


# ---------------------------------------------------------------------------
# GSTR-1 B2B Invoices
# ---------------------------------------------------------------------------

def get_gstr1_b2b(
    gstin: str,
    year: str,
    month: str,
    # BUG FIX: Added the 3 optional filter params the router was already passing
    action_required: Optional[str] = None,
    from_date: Optional[str] = None,
    counterparty_gstin: Optional[str] = None,
) -> Dict[str, Any]:

    session = get_session(gstin)

    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-1/b2b/{year}/{month}"

    headers = {
        "Authorization": token,
        "x-api-key": API_KEY,
        "x-api-version": API_VERSION,
        "x-source": "primary",
    }

    # Optional query params
    params: Dict[str, str] = {}
    if action_required:
        params["action_required"] = action_required
    if from_date:
        params["from_date"] = from_date
    if counterparty_gstin:
        params["counterparty_gstin"] = counterparty_gstin

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        payload = response.json()
    except Exception as e:
        return {"success": False, "message": "Failed to contact GST API", "error": str(e)}

    b2b_data = payload.get("data", {}).get("data", {}).get("b2b", [])

    invoices = []
    total_taxable = 0.0
    total_cgst = 0.0
    total_sgst = 0.0
    total_igst = 0.0
    total_invoice_value = 0.0

    for buyer in b2b_data:
        ctin = buyer.get("ctin")

        for inv in buyer.get("inv", []):
            # BUG FIX: Extract invoice_number, invoice_date, invoice_value from
            # the inv dict using the correct GST field names (inum, idt, val).
            # These were previously referenced as bare variables that were never defined,
            # causing a NameError at runtime on every B2B request.
            invoice_number = inv.get("inum")
            invoice_date = inv.get("idt")
            invoice_value = inv.get("val", 0.0)
            pos = inv.get("pos")
            reverse_charge = inv.get("rchrg")
            invoice_type = inv.get("inv_typ")

            taxable = 0.0
            cgst = 0.0
            sgst = 0.0
            igst = 0.0
            cess = 0.0
            tax_rate = None

            for itm in inv.get("itms", []):
                det = itm.get("itm_det", {})
                taxable += det.get("txval", 0) or 0
                cgst += det.get("camt", 0) or 0
                sgst += det.get("samt", 0) or 0
                igst += det.get("iamt", 0) or 0
                cess += det.get("csamt", 0) or 0
                tax_rate = det.get("rt")

            invoices.append({
                "counterparty_gstin": ctin,
                "invoice_number": invoice_number,
                "invoice_date": invoice_date,
                "place_of_supply": pos,
                "invoice_type": invoice_type,
                "reverse_charge": reverse_charge,
                "taxable_value": taxable,
                "tax_rate": tax_rate,
                "cgst": cgst,
                "sgst": sgst,
                "igst": igst,
                "cess": cess,
                "invoice_value": invoice_value,
            })

            total_taxable += taxable
            total_cgst += cgst
            total_sgst += sgst
            total_igst += igst
            total_invoice_value += invoice_value

    # ─────────────────────────────────────────────────────────────────────────────
    # PERSIST TO DATABASE
    # ─────────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = get_or_create_client(gstin, db_session)

            # Normalize filter parameters for unique constraint
            filter_action = action_required or ""
            filter_from = from_date or ""
            filter_cparty = counterparty_gstin or ""

            # Check if record already exists
            existing = db_session.query(Gstr1B2B).filter(
                Gstr1B2B.client_id == client.id,
                Gstr1B2B.year == year,
                Gstr1B2B.month == month,
                Gstr1B2B.filter_action_required == filter_action,
                Gstr1B2B.filter_from_date == filter_from,
                Gstr1B2B.filter_counterparty_gstin == filter_cparty,
            ).first()

            if existing:
                # Update existing record
                existing.total_invoices = len(invoices)
                existing.total_taxable_value = total_taxable
                existing.total_cgst = total_cgst
                existing.total_sgst = total_sgst
                existing.total_igst = total_igst
                existing.invoices = invoices
                existing.upstream_status_code = response.status_code
            else:
                # Create new record
                b2b_record = Gstr1B2B(
                    client_id=client.id,
                    year=year,
                    month=month,
                    filter_action_required=filter_action,
                    filter_from_date=filter_from,
                    filter_counterparty_gstin=filter_cparty,
                    total_invoices=len(invoices),
                    total_taxable_value=total_taxable,
                    total_cgst=total_cgst,
                    total_sgst=total_sgst,
                    total_igst=total_igst,
                    invoices=invoices,
                    upstream_status_code=response.status_code,
                )
                db_session.add(b2b_record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            # Log but don't fail the API response - data is still returned
            print(f"Database error saving GSTR1 B2B: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session: {e}")

    return {
        "success": True,
        "summary": {
            "total_invoices": len(invoices),
            "total_taxable_value": total_taxable,
            "total_cgst": total_cgst,
            "total_sgst": total_sgst,
            "total_igst": total_igst,
            "total_invoice_value": total_invoice_value,
        },
        "invoices": invoices,
        "raw": payload,
    }


# ---------------------------------------------------------------------------
# GSTR-1 Summary
# ---------------------------------------------------------------------------

def get_gstr1_summary(gstin: str, year: str, month: str, summary_type: str = "short") -> Dict[str, Any]:
    """
    Fetch GSTR1 summary from sandbox and return an interpretable structure.
    """

    # BUG FIX: Was importing get_session from services.session_storage_manager at
    # module level (duplicate, wrong path). Now uses the single top-level import.
    session = get_session(gstin)

    if not session:
        return {"success": False, "message": "No active session found for GSTIN"}

    token = session["access_token"]
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-1/{year}/{month}"

    params = {}
    if summary_type == "long":
        params["summary_type"] = "long"

    headers = {
        "Authorization": token,
        "x-api-key": API_KEY,
        "x-api-version": API_VERSION,
        "x-source": "primary",
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        data = resp.json()
    except Exception as e:
        return {"success": False, "message": "Failed to contact GST API", "error": str(e)}

    if resp.status_code != 200:
        return {"success": False, "status_code": resp.status_code, "response": data}

    payload = data.get("data", {}).get("data", {})

    interpreted_sections = []

    for sec in payload.get("sec_sum", []):
        section = {
            "sec_nm": sec.get("sec_nm"),
            "ttl_rec": sec.get("ttl_rec"),
            "ttl_val": sec.get("ttl_val"),
            "ttl_tax": sec.get("ttl_tax"),
            "ttl_igst": sec.get("ttl_igst"),
            "ttl_cgst": sec.get("ttl_cgst"),
            "ttl_sgst": sec.get("ttl_sgst"),
            "ttl_cess": sec.get("ttl_cess"),
            "chksum": sec.get("chksum"),
            "raw": sec,
        }

        if "cpty_sum" in sec:
            section["counterparties"] = sec["cpty_sum"]

        if "sub_sections" in sec:
            section["sub_sections"] = sec["sub_sections"]

        interpreted_sections.append(section)

    # ─────────────────────────────────────────────────────────────────────────────
    # PERSIST TO DATABASE
    # ─────────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = get_or_create_client(gstin, db_session)

            # Check if record already exists
            existing = db_session.query(Gstr1Summary).filter(
                Gstr1Summary.client_id == client.id,
                Gstr1Summary.year == year,
                Gstr1Summary.month == month,
                Gstr1Summary.summary_type == summary_type,
            ).first()

            ret_period = payload.get("ret_period")

            if existing:
                # Update existing record
                existing.ret_period = ret_period
                existing.sections = interpreted_sections
                existing.upstream_status_code = resp.status_code
            else:
                # Create new record
                summary_record = Gstr1Summary(
                    client_id=client.id,
                    year=year,
                    month=month,
                    summary_type=summary_type,
                    ret_period=ret_period,
                    sections=interpreted_sections,
                    upstream_status_code=resp.status_code,
                )
                db_session.add(summary_record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            # Log but don't fail the API response
            print(f"Database error saving GSTR1 Summary: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session: {e}")

    return {
        "success": True,
        "gstin": payload.get("gstin"),
        "ret_period": payload.get("ret_period"),
        "summary_type": summary_type,
        "newSumFlag": payload.get("newSumFlag"),
        "sections": interpreted_sections,
        "raw": payload,
    }


def get_gstr1_b2csa(gstin: str, year: str, month: str) -> Dict[str, Any]:
    """
    Fetch GSTR-1 B2CSA (Amended B2CS) data and return a readable structure.
    """

    session = get_session(gstin)

    if not session:
        return {
            "success": False,
            "message": "GST session not found. Verify OTP first.",
            "request": {"gstin": gstin, "year": year, "month": month}
        }

    token = session.get("access_token")

    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-1/b2csa/{year}/{month}"

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

    b2cs_data = (
        payload.get("data", {})
        .get("data", {})
        .get("data", {})
        .get("b2cs", [])
    )

    interpreted = []

    for entry in b2cs_data:
        interpreted.append({
            "place_of_supply": entry.get("pos"),
            "supply_type": entry.get("sply_ty"),
            "invoice_type": entry.get("typ"),
            "tax_rate": entry.get("rt"),
            "taxable_value": entry.get("txval"),
            "igst": entry.get("iamt"),
            "cgst": entry.get("camt"),
            "sgst": entry.get("samt"),
            "cess": entry.get("csamt"),
        })

    # ─────────────────────────────────────────────────────────────────────────────
    # PERSIST TO DATABASE
    # ─────────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = get_or_create_client(gstin, db_session)

            # Check if record already exists
            existing = db_session.query(Gstr1B2CSA).filter(
                Gstr1B2CSA.client_id == client.id,
                Gstr1B2CSA.year == year,
                Gstr1B2CSA.month == month,
            ).first()

            if existing:
                # Update existing record
                existing.records = interpreted
                existing.upstream_status_code = response.status_code
            else:
                # Create new record
                b2csa_record = Gstr1B2CSA(
                    client_id=client.id,
                    year=year,
                    month=month,
                    records=interpreted,
                    upstream_status_code=response.status_code,
                )
                db_session.add(b2csa_record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving GSTR1 B2CSA: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session: {e}")

    return {
        "success": True,
        "request": {
            "gstin": gstin,
            "year": year,
            "month": month,
            "endpoint": "GSTR-1 B2CSA"
        },
        "upstream_status_code": response.status_code,
        "records": interpreted,
        "raw": payload
    }





def get_gstr1_b2cs(gstin: str, year: str, month: str) -> Dict[str, Any]:
    """
    Fetch GSTR-1 B2CS (Business to Consumer Small) data.
    """

    session = get_session(gstin)

    if not session:
        return {
            "success": False,
            "message": "GST session not found. Verify OTP first.",
            "request": {
                "gstin": gstin,
                "year": year,
                "month": month
            }
        }

    token = session.get("access_token")

    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-1/b2cs/{year}/{month}"

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
            "error": str(e)
        }

    # Extract B2CS data from nested payload
    b2cs_data = (
        payload.get("data", {})
        .get("data", {})
        .get("b2cs", [])
    )

    interpreted = []

    for entry in b2cs_data:
        interpreted.append({
            "place_of_supply": entry.get("pos"),
            "supply_type": entry.get("sply_ty"),
            "invoice_type": entry.get("typ"),
            "tax_rate": entry.get("rt"),
            "taxable_value": entry.get("txval"),
            "igst": entry.get("iamt"),
            "cgst": entry.get("camt"),
            "sgst": entry.get("samt"),
            "cess": entry.get("csamt"),
            "checksum": entry.get("chksum"),
            "flag": entry.get("flag")
        })

    # ─────────────────────────────────────────────────────────────────────────────
    # PERSIST TO DATABASE
    # ─────────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = get_or_create_client(gstin, db_session)

            # Check if record already exists
            existing = db_session.query(Gstr1B2CS).filter(
                Gstr1B2CS.client_id == client.id,
                Gstr1B2CS.year == year,
                Gstr1B2CS.month == month,
            ).first()

            if existing:
                # Update existing record
                existing.records = interpreted
                existing.upstream_status_code = response.status_code
            else:
                # Create new record
                b2cs_record = Gstr1B2CS(
                    client_id=client.id,
                    year=year,
                    month=month,
                    records=interpreted,
                    upstream_status_code=response.status_code,
                )
                db_session.add(b2cs_record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving GSTR1 B2CS: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session: {e}")

    return {
        "success": True,
        "request": {
            "gstin": gstin,
            "year": year,
            "month": month,
            "endpoint": "GSTR-1 B2CS"
        },
        "upstream_status_code": response.status_code,
        "records": interpreted,
        "raw": payload
    }


def get_gstr1_cdnr(
    gstin: str,
    year: str,
    month: str,
    action_required: Optional[str] = None,
    from_date: Optional[str] = None,
) -> Dict[str, Any]:

    session = get_session(gstin)

    if not session:
        return {
            "success": False,
            "message": "GST session not found. Verify OTP first.",
            "request": {"gstin": gstin, "year": year, "month": month},
        }

    token = session.get("access_token")

    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-1/cdnr/{year}/{month}"

    headers = {
        "Authorization": token,
        "x-api-key": API_KEY,
        "x-api-version": API_VERSION,
        "x-source": "primary",
    }

    params = {}

    if action_required:
        params["action_required"] = action_required

    if from_date:
        params["from"] = from_date

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )

        payload = response.json()

    except Exception as e:
        return {
            "success": False,
            "message": "Failed to contact GST API",
            "error": str(e),
        }

    data = payload.get("data", {})

    if data.get("status_cd") == "0":
        return {
            "success": True,
            "message": data.get("error", {}).get("message"),
            "records": [],
            "raw": payload,
        }

    cdnr_data = data.get("data", {}).get("cdnr", [])

    interpreted = []

    for entry in cdnr_data:
        ctin = entry.get("ctin")
        cfs = entry.get("cfs")

        for note in entry.get("nt", []):

            items = []

            for item in note.get("itms", []):
                det = item.get("itm_det", {})

                items.append(
                    {
                        "item_number": item.get("num"),
                        "tax_rate": det.get("rt"),
                        "taxable_value": det.get("txval"),
                        "igst": det.get("iamt"),
                        "cgst": det.get("camt"),
                        "sgst": det.get("samt"),
                        "cess": det.get("csamt"),
                    }
                )

            interpreted.append(
                {
                    "counterparty_gstin": ctin,
                    "counter_filing_status": cfs,
                    "note_number": note.get("nt_num"),
                    "note_date": note.get("nt_dt"),
                    "note_type": note.get("ntty"),
                    "invoice_type": note.get("inv_typ"),
                    "place_of_supply": note.get("pos"),
                    "reverse_charge": note.get("rchrg"),
                    "note_value": note.get("val"),
                    "flag": note.get("flag"),
                    "delete_flag": note.get("d_flag"),
                    "updated_by": note.get("updby"),
                    "checksum": note.get("chksum"),
                    "items": items,
                }
            )

    # ─────────────────────────────────────────────────────────────────────────────
    # PERSIST TO DATABASE
    # ─────────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = get_or_create_client(gstin, db_session)

            # Normalize filter parameters for unique constraint
            filter_action = action_required or ""
            filter_from = from_date or ""

            # Check if record already exists
            existing = db_session.query(Gstr1CDNR).filter(
                Gstr1CDNR.client_id == client.id,
                Gstr1CDNR.year == year,
                Gstr1CDNR.month == month,
                Gstr1CDNR.filter_action_required == filter_action,
                Gstr1CDNR.filter_from_date == filter_from,
            ).first()

            if existing:
                # Update existing record
                existing.record_count = len(interpreted)
                existing.records = interpreted
                existing.upstream_status_code = response.status_code
            else:
                # Create new record
                cdnr_record = Gstr1CDNR(
                    client_id=client.id,
                    year=year,
                    month=month,
                    filter_action_required=filter_action,
                    filter_from_date=filter_from,
                    record_count=len(interpreted),
                    records=interpreted,
                    upstream_status_code=response.status_code,
                )
                db_session.add(cdnr_record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving GSTR1 CDNR: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session: {e}")

    return {
        "success": True,
        "request": {
            "gstin": gstin,
            "year": year,
            "month": month,
            "action_required": action_required,
            "from": from_date,
            "endpoint": "GSTR-1 CDNR",
        },
        "upstream_status_code": response.status_code,
        "record_count": len(interpreted),
        "records": interpreted,
        "raw": payload,
    }

def get_gstr1_doc_issue(gstin: str, year: str, month: str) -> Dict[str, Any]:
    """
    Fetch GSTR-1 Document Issued data and return a readable structure.
    """
    session = get_session(gstin)
    if not session:
        return {
            "success": False,
            "message": "GST session not found. Verify OTP first.",
            "request": {"gstin": gstin, "year": year, "month": month}
        }

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-1/doc-issue/{year}/{month}"
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

    doc_issue = (
        payload.get("data", {})
               .get("data", {})
               .get("doc_issue", {})
    )

    interpreted = []
    for doc_det in doc_issue.get("doc_det", []):
        doc_num = doc_det.get("doc_num")
        docs = doc_det.get("docs", [])
        if not docs:
            continue
        for doc in docs:
            interpreted.append({
                "document_type_number": doc_num,
                "serial_number": doc.get("num"),
                "from_serial": doc.get("from"),
                "to_serial": doc.get("to"),
                "total_issued": doc.get("totnum"),
                "cancelled": doc.get("cancel"),
                "net_issued": doc.get("net_issue"),
            })

    # ─────────────────────────────────────────────────────────────────────────────
    # PERSIST TO DATABASE
    # ─────────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = get_or_create_client(gstin, db_session)

            # Check if record already exists
            existing = db_session.query(Gstr1DocIssue).filter(
                Gstr1DocIssue.client_id == client.id,
                Gstr1DocIssue.year == year,
                Gstr1DocIssue.month == month,
            ).first()

            if existing:
                # Update existing record
                existing.records = interpreted
                existing.upstream_status_code = response.status_code
            else:
                # Create new record
                doc_issue_record = Gstr1DocIssue(
                    client_id=client.id,
                    year=year,
                    month=month,
                    records=interpreted,
                    upstream_status_code=response.status_code,
                )
                db_session.add(doc_issue_record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving GSTR1 Document Issue: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session: {e}")

    return {
        "success": True,
        "request": {
            "gstin": gstin,
            "year": year,
            "month": month,
            "endpoint": "GSTR-1 Document Issued"
        },
        "upstream_status_code": response.status_code,
        "records": interpreted,
        "raw": payload
    }

def get_gstr1_hsn(gstin: str, year: str, month: str) -> Dict[str, Any]:
    """
    Fetch GSTR-1 HSN Summary data and return a readable structure.
    """
    session = get_session(gstin)
    if not session:
        return {
            "success": False,
            "message": "GST session not found. Verify OTP first.",
            "request": {"gstin": gstin, "year": year, "month": month}
        }

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-1/hsn/{year}/{month}"
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

    hsn_data = (
        payload.get("data", {})
               .get("data", {})
               .get("hsn", {})
               .get("data", [])
    )

    interpreted = []
    for entry in hsn_data:
        interpreted.append({
            "serial_number": entry.get("num"),
            "hsn_sac_code": entry.get("hsn_sc"),
            "description": entry.get("desc"),
            "unit_of_quantity": entry.get("uqc"),
            "quantity": entry.get("qty"),
            "tax_rate": entry.get("rt"),
            "taxable_value": entry.get("txval"),
            "igst": entry.get("iamt"),
            "cgst": entry.get("camt"),
            "sgst": entry.get("samt"),
        })

    # ─────────────────────────────────────────────────────────────────────────────
    # PERSIST TO DATABASE
    # ─────────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = get_or_create_client(gstin, db_session)

            # Check if record already exists
            existing = db_session.query(Gstr1HSN).filter(
                Gstr1HSN.client_id == client.id,
                Gstr1HSN.year == year,
                Gstr1HSN.month == month,
            ).first()

            if existing:
                # Update existing record
                existing.records = interpreted
                existing.upstream_status_code = response.status_code
            else:
                # Create new record
                hsn_record = Gstr1HSN(
                    client_id=client.id,
                    year=year,
                    month=month,
                    records=interpreted,
                    upstream_status_code=response.status_code,
                )
                db_session.add(hsn_record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving GSTR1 HSN: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session: {e}")

    return {
        "success": True,
        "request": {
            "gstin": gstin,
            "year": year,
            "month": month,
            "endpoint": "GSTR-1 HSN Summary"
        },
        "upstream_status_code": response.status_code,
        "records": interpreted,
        "raw": payload
    }

def get_gstr1_nil(gstin: str, year: str, month: str) -> Dict[str, Any]:
    """
    Fetch GSTR-1 Nil-rated, Exempted and Non-GST supplies data and return a readable structure.
    """
    session = get_session(gstin)
    if not session:
        return {
            "success": False,
            "message": "GST session not found. Verify OTP first.",
            "request": {"gstin": gstin, "year": year, "month": month}
        }

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-1/nil/{year}/{month}"
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

    nil_inv = (
        payload.get("data", {})
               .get("data", {})
               .get("nil", {})
               .get("inv", [])
    )

    SUPPLY_TYPE_LABELS = {
        "INTRAB2B": "Intra-state B2B",
        "INTRAB2C": "Intra-state B2C",
        "INTRB2B":  "Inter-state B2B",
        "INTRB2C":  "Inter-state B2C",
    }

    interpreted = []
    for entry in nil_inv:
        sply_ty = entry.get("sply_ty")
        interpreted.append({
            "supply_type_code": sply_ty,
            "supply_type": SUPPLY_TYPE_LABELS.get(sply_ty, sply_ty),
            "nil_rated_amount": entry.get("nil_amt"),
            "exempted_amount": entry.get("expt_amt"),
            "non_gst_amount": entry.get("ngsup_amt"),
        })

    # ─────────────────────────────────────────────────────────────────────────────
    # PERSIST TO DATABASE
    # ─────────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = get_or_create_client(gstin, db_session)

            # Check if record already exists
            existing = db_session.query(Gstr1Nil).filter(
                Gstr1Nil.client_id == client.id,
                Gstr1Nil.year == year,
                Gstr1Nil.month == month,
            ).first()

            if existing:
                # Update existing record
                existing.records = interpreted
                existing.upstream_status_code = response.status_code
            else:
                # Create new record
                nil_record = Gstr1Nil(
                    client_id=client.id,
                    year=year,
                    month=month,
                    records=interpreted,
                    upstream_status_code=response.status_code,
                )
                db_session.add(nil_record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving GSTR1 Nil: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session: {e}")

    return {
        "success": True,
        "request": {
            "gstin": gstin,
            "year": year,
            "month": month,
            "endpoint": "GSTR-1 Nil Rated"
        },
        "upstream_status_code": response.status_code,
        "records": interpreted,
        "raw": payload
    }



def get_gstr1_b2cl(gstin: str, year: str, month: str, state_code: str = None) -> Dict[str, Any]:
    """
    Fetch GSTR-1 B2CL (B2C Large invoices) data and return a readable structure.
    """
    session = get_session(gstin)
    if not session:
        return {
            "success": False,
            "message": "GST session not found. Verify OTP first.",
            "request": {"gstin": gstin, "year": year, "month": month}
        }

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-1/b2cl/{year}/{month}"
    headers = {
        "Authorization": token,
        "x-api-key": API_KEY,
        "x-api-version": API_VERSION,
        "x-source": "primary"
    }

    params = {}
    if state_code:
        params["state_code"] = state_code

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        payload = response.json()
    except Exception as e:
        return {
            "success": False,
            "message": "Failed to contact GST API",
            "error": str(e),
        }

    b2cl_data = (
        payload.get("data", {})
               .get("data", {})
               .get("b2cl", [])
    )

    interpreted = []
    for entry in b2cl_data:
        pos = entry.get("pos")
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
                "place_of_supply": pos,
                "invoice_number": inv.get("inum"),
                "invoice_date": inv.get("idt"),
                "invoice_value": inv.get("val"),
                "flag": inv.get("flag"),
                "items": items,
            })

    # ─────────────────────────────────────────────────────────────────────────────
    # PERSIST TO DATABASE
    # ─────────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = get_or_create_client(gstin, db_session)

            # Check if record already exists
            existing = db_session.query(Gstr1B2CL).filter(
                Gstr1B2CL.client_id == client.id,
                Gstr1B2CL.year == year,
                Gstr1B2CL.month == month,
            ).first()

            if existing:
                # Update existing record
                existing.records = interpreted
                existing.upstream_status_code = response.status_code
            else:
                # Create new record
                b2cl_record = Gstr1B2CL(
                    client_id=client.id,
                    year=year,
                    month=month,
                    records=interpreted,
                    upstream_status_code=response.status_code,
                )
                db_session.add(b2cl_record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving GSTR1 B2CL: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session: {e}")

    return {
        "success": True,
        "request": {
            "gstin": gstin,
            "year": year,
            "month": month,
            "state_code": state_code,
            "endpoint": "GSTR-1 B2CL"
        },
        "upstream_status_code": response.status_code,
        "records": interpreted,
        "raw": payload
    }

def get_gstr1_cdnur(gstin: str, year: str, month: str) -> Dict[str, Any]:
    """
    Fetch GSTR-1 CDNUR (Credit/Debit Notes for Unregistered Users) data and return a readable structure.
    """
    session = get_session(gstin)
    if not session:
        return {
            "success": False,
            "message": "GST session not found. Verify OTP first.",
            "request": {"gstin": gstin, "year": year, "month": month}
        }

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-1/cdnur/{year}/{month}"
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

    cdnur_data = (
        payload.get("data", {})
               .get("data", {})
               .get("cdnur", [])
    )

    NOTE_TYPE_LABELS = {
        "C": "Credit Note",
        "D": "Debit Note",
    }

    SUPPLY_TYPE_LABELS = {
        "EXPWP":  "Export with Payment",
        "EXPWOP": "Export without Payment",
        "B2CL":   "B2C Large",
    }

    interpreted = []
    for entry in cdnur_data:
        items = []
        for item in entry.get("itms", []):
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

        ntty = entry.get("ntty")
        typ = entry.get("typ")
        interpreted.append({
            "note_number": entry.get("nt_num"),
            "note_date": entry.get("nt_dt"),
            "note_type_code": ntty,
            "note_type": NOTE_TYPE_LABELS.get(ntty, ntty),
            "supply_type_code": typ,
            "supply_type": SUPPLY_TYPE_LABELS.get(typ, typ),
            "note_value": entry.get("val"),
            "flag": entry.get("flag"),
            "delete_flag": entry.get("d_flag"),
            "items": items,
        })

    # ─────────────────────────────────────────────────────────────────────────────
    # PERSIST TO DATABASE
    # ─────────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = get_or_create_client(gstin, db_session)

            # Check if record already exists
            existing = db_session.query(Gstr1CDNUR).filter(
                Gstr1CDNUR.client_id == client.id,
                Gstr1CDNUR.year == year,
                Gstr1CDNUR.month == month,
            ).first()

            if existing:
                # Update existing record
                existing.records = interpreted
                existing.upstream_status_code = response.status_code
            else:
                # Create new record
                cdnur_record = Gstr1CDNUR(
                    client_id=client.id,
                    year=year,
                    month=month,
                    records=interpreted,
                    upstream_status_code=response.status_code,
                )
                db_session.add(cdnur_record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving GSTR1 CDNUR: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session: {e}")

    return {
        "success": True,
        "request": {
            "gstin": gstin,
            "year": year,
            "month": month,
            "endpoint": "GSTR-1 CDNUR"
        },
        "upstream_status_code": response.status_code,
        "records": interpreted,
        "raw": payload
    }


def get_gstr1_exp(gstin: str, year: str, month: str) -> Dict[str, Any]:
    """
    Fetch GSTR-1 EXP (Export invoices) data and return a readable structure.
    """
    session = get_session(gstin)
    if not session:
        return {
            "success": False,
            "message": "GST session not found. Verify OTP first.",
            "request": {"gstin": gstin, "year": year, "month": month}
        }

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-1/exp/{year}/{month}"
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

    exp_data = (
        payload.get("data", {})
               .get("data", {})
               .get("exp", [])
    )

    EXPORT_TYPE_LABELS = {
        "WPAY":  "Export with Payment of Tax",
        "WOPAY": "Export without Payment of Tax",
    }

    interpreted = []
    for entry in exp_data:
        exp_typ = entry.get("exp_typ")
        for inv in entry.get("inv", []):
            items = []
            for item in inv.get("itms", []):
                items.append({
                    "tax_rate": item.get("rt"),
                    "taxable_value": item.get("txval"),
                    "igst": item.get("iamt"),
                    "cess": item.get("csamt"),
                })
            interpreted.append({
                "export_type_code": exp_typ,
                "export_type": EXPORT_TYPE_LABELS.get(exp_typ, exp_typ),
                "invoice_number": inv.get("inum"),
                "invoice_date": inv.get("idt"),
                "invoice_value": inv.get("val"),
                "flag": inv.get("flag"),
                "items": items,
            })

    # ─────────────────────────────────────────────────────────────────────────────
    # PERSIST TO DATABASE
    # ─────────────────────────────────────────────────────────────────────────────
    try:
        db_session = get_sync_db()
        try:
            client = get_or_create_client(gstin, db_session)

            # Check if record already exists
            existing = db_session.query(Gstr1EXP).filter(
                Gstr1EXP.client_id == client.id,
                Gstr1EXP.year == year,
                Gstr1EXP.month == month,
            ).first()

            if existing:
                # Update existing record
                existing.records = interpreted
                existing.upstream_status_code = response.status_code
            else:
                # Create new record
                exp_record = Gstr1EXP(
                    client_id=client.id,
                    year=year,
                    month=month,
                    records=interpreted,
                    upstream_status_code=response.status_code,
                )
                db_session.add(exp_record)

            db_session.commit()
        except Exception as db_error:
            db_session.rollback()
            print(f"Database error saving GSTR1 EXP: {db_error}")
        finally:
            db_session.close()
    except Exception as e:
        print(f"Failed to get database session: {e}")

    return {
        "success": True,
        "request": {
            "gstin": gstin,
            "year": year,
            "month": month,
            "endpoint": "GSTR-1 EXP"
        },
        "upstream_status_code": response.status_code,
        "records": interpreted,
        "raw": payload
    }


def get_gstr1_txp(gstin: str, year: str, month: str, counterparty_gstin: Optional[str] = None, action_required: Optional[str] = None, from_date: Optional[str] = None) -> Dict[str, Any]:

    session = get_session(gstin)
    if not session:
        return {"success": False, "message": "GST session not found"}

    token = session.get("access_token")
    url = f"{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-1/txp/{year}/{month}"

    headers = {
        "Authorization": token,
        "x-api-key":     API_KEY,
        "x-api-version": API_VERSION,
        "x-source":      "primary",
    }

    params = {}
    if counterparty_gstin:
        params["counterparty_gstin"] = counterparty_gstin
    if action_required:
        params["action_required"] = action_required
    if from_date:
        params["from"] = from_date

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
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

    # ── txpd: advance tax paid entries ────────────────────────────────────────
    # Each entry represents an advance receipt row with place-of-supply,
    # supply type, and per-rate tax breakdowns.
    #
    # flag:    "N" = no action needed / already processed
    #          "Y" = action required by taxpayer
    # sply_ty: "INTRA" = intra-state | "INTER" = inter-state
    # pos:     place of supply state code (2-digit)
    # chksum:  server-side checksum for this record

    def _parse_txpd_item(itm: dict) -> Dict[str, Any]:
        return {
            "tax_rate":        itm.get("rt"),
            "advance_amount":  itm.get("ad_amt", 0) or 0.0,
            "cgst":            itm.get("camt",   0) or 0.0,
            "sgst":            itm.get("samt",   0) or 0.0,
            "cess":            itm.get("csamt",  0) or 0.0,
            # igst is absent on INTRA supplies; will be present on INTER
            "igst":            itm.get("iamt",   0) or 0.0,
        }

    def _parse_txpd_entry(entry: dict) -> Dict[str, Any]:
        items = [_parse_txpd_item(i) for i in (entry.get("itms") or [])]

        # Roll-up totals across all rate slabs for this POS entry
        total_advance  = sum(i["advance_amount"] for i in items)
        total_igst     = sum(i["igst"]           for i in items)
        total_cgst     = sum(i["cgst"]           for i in items)
        total_sgst     = sum(i["sgst"]           for i in items)
        total_cess     = sum(i["cess"]           for i in items)
        total_tax      = total_igst + total_cgst + total_sgst + total_cess

        return {
            "pos":          entry.get("pos"),       # place of supply state code
            "supply_type":  entry.get("sply_ty"),   # "INTRA" | "INTER"
            "flag":         entry.get("flag"),       # "Y" = action required, "N" = none
            "action_required": entry.get("flag") == "Y",
            "checksum":     entry.get("chksum"),

            # Per-rate-slab breakdown
            "items": items,

            # Aggregate across all slabs for this entry
            "totals": {
                "advance_amount": total_advance,
                "igst":           total_igst,
                "cgst":           total_cgst,
                "sgst":           total_sgst,
                "cess":           total_cess,
                "total_tax":      total_tax,
            },
        }

    txpd_entries = [_parse_txpd_entry(e) for e in (inner.get("txpd") or [])]

    # Grand summary across all POS entries
    grand_advance = sum(e["totals"]["advance_amount"] for e in txpd_entries)
    grand_igst    = sum(e["totals"]["igst"]           for e in txpd_entries)
    grand_cgst    = sum(e["totals"]["cgst"]           for e in txpd_entries)
    grand_sgst    = sum(e["totals"]["sgst"]           for e in txpd_entries)
    grand_cess    = sum(e["totals"]["cess"]            for e in txpd_entries)

    return {
        "success":      True,
        "status_cd":    status_cd,

        # Advance tax paid (TXP) entries grouped by place of supply
        "txpd":         txpd_entries,
        "entry_count":  len(txpd_entries),

        # Grand totals across all POS entries
        "grand_totals": {
            "advance_amount": grand_advance,
            "igst":           grand_igst,
            "cgst":           grand_cgst,
            "sgst":           grand_sgst,
            "cess":           grand_cess,
            "total_tax":      grand_igst + grand_cgst + grand_sgst + grand_cess,
        },

        "raw": payload,
    }