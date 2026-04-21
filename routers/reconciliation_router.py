import base64
import io
import json

from fastapi import APIRouter, Form, HTTPException, UploadFile, File, Query

from database.core.database import get_sync_db
from database.models.client import Client
from database.services.gstr2b.models import Gstr2B
from services.gstr_2B_service import get_gstr2b
import importlib as _il

_recon = _il.import_module("services.2B_reconciliation_service")
convert_2b_records_to_df = _recon.convert_2b_records_to_df
convert_cdnr_records_to_df = _recon.convert_cdnr_records_to_df
read_books_file = _recon.read_books_file
read_2b_file = _recon.read_2b_file
auto_map_columns = _recon.auto_map_columns
process_reconciliation = _recon.process_reconciliation
compute_summary_metrics = _recon.compute_summary_metrics
export_to_excel_combined = _recon.export_to_excel_combined
generate_html_report_combined = _recon.generate_html_report_combined

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


def _get_all_records(gstin: str, year: str, month: str) -> list[dict]:
    """Query DB for ALL records from Gstr2B for the given period."""
    db = get_sync_db()
    try:
        client = db.query(Client).filter(Client.gstin == gstin).first()
        if not client:
            return []

        rows = (
            db.query(Gstr2B)
            .filter(
                Gstr2B.client_id == client.id,
                Gstr2B.year == year,
                Gstr2B.month == month,
            )
            .all()
        )

        all_records = []
        for row in rows:
            if row.records:
                all_records.extend(row.records)
        return all_records
    finally:
        db.close()


def _split_records_by_section(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split records into B2B and CDNR (including CDNRA) lists."""
    b2b = []
    cdnr = []
    for r in records:
        section = r.get("section", "")
        if section in ("cdnr", "cdnra"):
            cdnr.append(r)
        elif section in ("b2b", "b2ba", ""):
            # Records without a section tag are assumed B2B (legacy data)
            b2b.append(r)
    return b2b, cdnr


def _get_2b_info(gstin: str, year: str, month: str) -> dict:
    """Return metadata about stored 2B data for a period."""
    all_records = _get_all_records(gstin, year, month)
    if not all_records:
        return {
            "available": False, "record_count": 0,
            "b2b_count": 0, "cdnr_count": 0,
            "response_type": None, "gen_date": None,
        }

    b2b, cdnr = _split_records_by_section(all_records)

    # Get metadata from DB row
    db = get_sync_db()
    try:
        client = db.query(Client).filter(Client.gstin == gstin).first()
        row = (
            db.query(Gstr2B)
            .filter(Gstr2B.client_id == client.id, Gstr2B.year == year, Gstr2B.month == month)
            .first()
        ) if client else None
        return {
            "available": True,
            "record_count": len(all_records),
            "b2b_count": len(b2b),
            "cdnr_count": len(cdnr),
            "response_type": row.response_type if row else None,
            "gen_date": row.gen_date if row else None,
        }
    finally:
        db.close()


@router.get("/check-2b/{gstin}/{year}/{month}")
def check_2b_data(gstin: str, year: str, month: str):
    """Check whether 2B data exists in DB for this GSTIN/period."""
    return _get_2b_info(gstin, year, month)


REQUIRED_FIELDS = ["GSTIN", "Party Name", "Invoice No", "Invoice Date",
                   "Taxable Value", "CGST", "SGST", "IGST"]


@router.post("/extract-columns/{gstin}/{year}/{month}")
async def extract_columns(
    gstin: str, year: str, month: str,
    books_file: UploadFile = File(...),
):
    """Parse books Excel + DB 2B data and return column names with auto-mapped suggestions."""
    # Read uploaded books file
    try:
        contents = await books_file.read()
        df_books = read_books_file(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read books file: {str(e)}")

    books_columns = [str(c) for c in df_books.columns.tolist()]
    books_mapping = auto_map_columns(df_books.columns)
    # Invert to {standard_field: original_col} for frontend convenience
    books_mapping_inv = {v: k for k, v in books_mapping.items()}

    # Get 2B columns from DB
    all_records = _get_all_records(gstin, year, month)
    b2b_records, cdnr_records = _split_records_by_section(all_records)

    t2b_columns: list[str] = []
    t2b_mapping_inv: dict = {}
    if b2b_records:
        df_2b = convert_2b_records_to_df(b2b_records)
        t2b_columns = [str(c) for c in df_2b.columns.tolist()]
        t2b_map = auto_map_columns(df_2b.columns)
        t2b_mapping_inv = {v: k for k, v in t2b_map.items()}

    return {
        "books_columns": books_columns,
        "t2b_columns": t2b_columns,
        "books_mapping": books_mapping_inv,
        "t2b_mapping": t2b_mapping_inv,
        "required_fields": REQUIRED_FIELDS,
    }


@router.post("/run/{gstin}/{year}/{month}")
async def run_reconciliation(
    gstin: str,
    year: str,
    month: str,
    books_file: UploadFile = File(...),
    fetch_2b: bool = Query(False),
    books_mapping_json: str = Form(None),
    t2b_mapping_json: str = Form(None),
):
    """Run 2B reconciliation: upload books Excel, match against stored 2B data.

    Runs B2B and CDNR reconciliation separately, returns combined results.
    Optionally accepts user-provided column mappings as JSON strings
    (format: {standard_field: original_col}).
    """
    # Parse optional user-provided mappings (inverted: {standard_field: orig_col} → {orig_col: standard_field})
    user_books_map = None
    user_t2b_map = None
    if books_mapping_json:
        try:
            inv = json.loads(books_mapping_json)
            user_books_map = {v: k for k, v in inv.items() if v}
        except (json.JSONDecodeError, AttributeError):
            pass
    if t2b_mapping_json:
        try:
            inv = json.loads(t2b_mapping_json)
            user_t2b_map = {v: k for k, v in inv.items() if v}
        except (json.JSONDecodeError, AttributeError):
            pass

    # Optionally fetch fresh 2B data from GST API
    if fetch_2b:
        result = get_gstr2b(gstin, year, month)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail="Failed to fetch 2B data from GST API")

    # Get all records from DB, split by section
    all_records = _get_all_records(gstin, year, month)
    if not all_records:
        raise HTTPException(status_code=400, detail="No 2B data found for this period. Fetch 2B data first.")

    b2b_records, cdnr_records = _split_records_by_section(all_records)

    if not b2b_records and not cdnr_records:
        raise HTTPException(status_code=400, detail="No B2B or CDNR data found for this period.")

    # Read uploaded books file
    try:
        contents = await books_file.read()
        df_books = read_books_file(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read books file: {str(e)}")

    # --- B2B Reconciliation ---
    b2b_result = _run_section_recon(b2b_records, df_books, section="b2b",
                                    user_books_map=user_books_map, user_t2b_map=user_t2b_map)

    # --- CDNR Reconciliation ---
    cdnr_result = _run_section_recon(cdnr_records, df_books, section="cdnr",
                                     user_books_map=user_books_map, user_t2b_map=user_t2b_map)

    # Combined summary
    combined_summary = {}
    for key in b2b_result["summary"]:
        combined_summary[key] = b2b_result["summary"][key] + cdnr_result["summary"][key]

    # Generate combined Excel report
    excel_bytes = export_to_excel_combined(
        b2b_result["matched_df"], b2b_result["un_books_df"], b2b_result["un_2b_df"],
        b2b_result["df_books"], b2b_result["df_2b"], b2b_result["b_map"], b2b_result["t_map"],
        cdnr_result["matched_df"], cdnr_result["un_books_df"], cdnr_result["un_2b_df"],
        cdnr_result["df_books"], cdnr_result["df_2b"], cdnr_result["b_map"], cdnr_result["t_map"],
    )
    excel_b64 = base64.b64encode(excel_bytes).decode("utf-8")

    # Generate combined HTML report
    html_report = generate_html_report_combined(
        b2b_result["matched_df"], b2b_result["un_books_df"], b2b_result["un_2b_df"],
        b2b_result["summary"],
        cdnr_result["matched_df"], cdnr_result["un_books_df"], cdnr_result["un_2b_df"],
        cdnr_result["summary"],
        combined_summary,
    )

    return {
        "success": True,
        "b2b": {
            "summary": b2b_result["summary"],
            "matched": df_to_records(b2b_result["matched_df"]),
            "un_books": df_to_records(b2b_result["un_books_df"]),
            "un_2b": df_to_records(b2b_result["un_2b_df"]),
        },
        "cdnr": {
            "summary": cdnr_result["summary"],
            "matched": df_to_records(cdnr_result["matched_df"]),
            "un_books": df_to_records(cdnr_result["un_books_df"]),
            "un_2b": df_to_records(cdnr_result["un_2b_df"]),
        },
        "combined_summary": combined_summary,
        "excel_base64": excel_b64,
        "html_report": html_report,
    }


def _run_section_recon(records_2b: list[dict], df_books, section: str,
                       user_books_map=None, user_t2b_map=None) -> dict:
    """Run reconciliation for a single section (b2b or cdnr).

    Returns dict with DataFrames and summary for further composition.
    Accepts optional pre-built mappings from the user; falls back to auto_map_columns.
    """
    import pandas as pd

    empty_summary = {
        "books_total_itc": 0, "t2b_total_itc": 0, "matched_itc": 0,
        "books_risk_itc": 0, "t2b_risk_itc": 0,
        "books_invoice_count": 0, "t2b_invoice_count": 0,
        "matched_count": 0, "un_books_count": 0, "un_2b_count": 0,
    }

    if not records_2b:
        empty_df = pd.DataFrame()
        return {
            "summary": empty_summary,
            "matched_df": empty_df, "un_books_df": empty_df, "un_2b_df": empty_df,
            "df_books": df_books, "df_2b": empty_df,
            "b_map": {}, "t_map": {},
        }

    if section == "cdnr":
        df_2b = convert_cdnr_records_to_df(records_2b)
    else:
        df_2b = convert_2b_records_to_df(records_2b)

    b_map = user_books_map if user_books_map else auto_map_columns(df_books.columns)
    t_map = user_t2b_map if user_t2b_map else auto_map_columns(df_2b.columns)

    matched, un_books, un_2b = process_reconciliation(df_books, df_2b, b_map, t_map)
    summary = compute_summary_metrics(matched, un_books, un_2b, df_books, df_2b, b_map, t_map)

    return {
        "summary": summary,
        "matched_df": matched, "un_books_df": un_books, "un_2b_df": un_2b,
        "df_books": df_books, "df_2b": df_2b,
        "b_map": b_map, "t_map": t_map,
    }


def df_to_records(df):
    """Serialize a DataFrame to JSON-safe list of dicts."""
    import pandas as pd
    if df.empty:
        return []
    df_safe = df.copy()
    for col in df_safe.columns:
        if df_safe[col].dtype == "datetime64[ns]":
            df_safe[col] = df_safe[col].astype(str)
    return df_safe.fillna("").to_dict(orient="records")
