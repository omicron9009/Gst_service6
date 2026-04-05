import pandas as pd
import numpy as np
import re
from rapidfuzz import fuzz
import io
import xlsxwriter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_inv(inv):
    """Strip non-alphanumeric characters and uppercase an invoice number."""
    if pd.isna(inv) or inv == '':
        return ""
    return re.sub(r'[^A-Z0-9]', '', str(inv).upper())


def deduplicate_columns(df):
    """Rename duplicate column names by appending a suffix."""
    s = pd.Series(df.columns)
    dups = s[s.duplicated()].unique()
    for dup in dups:
        idx = s[s == dup].index
        for i, loc in enumerate(idx):
            if i != 0:
                s[loc] = f"{dup}_{i}"
    df.columns = s


def safe_sum(df, col):
    """Return the sum of *col* in *df*, or 0 when the column is missing / df is empty."""
    if df.empty or col not in df.columns:
        return 0
    return df[col].sum()


def get_mapped_sum(df, mapping, fields):
    """Sum the columns in *df* whose mapping value is in *fields*."""
    cols = [src for src, tgt in mapping.items() if tgt in fields]
    if not cols or df.empty:
        return 0
    return df[cols].apply(pd.to_numeric, errors='coerce').sum().sum()


def auto_map_columns(df_columns, required_cols=None):
    """Return a dict {original_col: standard_col} using regex pattern matching.

    Handles real-world GST Excel column-name variations such as
    "GSTIN of Supplier", "Integrated Tax - Tax Amount", "Inv No.", etc.

    *required_cols* defaults to the standard GST reconciliation fields.
    """
    if required_cols is None:
        required_cols = [
            "GSTIN", "Party Name", "Invoice No", "Invoice Date",
            "Taxable Value", "CGST", "SGST", "IGST",
        ]

    # Ordered list of regex patterns per standard field.
    # First match wins, so more specific patterns come first.
    _PATTERNS = {
        "GSTIN": re.compile(
            r"gstin|gst\s*in|gstn|gst\s*no|gst\s*number|uin",
            re.IGNORECASE,
        ),
        "Party Name": re.compile(
            r"party\s*name|trade.*name|legal.*name|supplier.*name"
            r"|name.*supplier|vendor.*name|name.*vendor"
            r"|customer.*name|name.*party|dealer.*name",
            re.IGNORECASE,
        ),
        "Invoice No": re.compile(
            r"inv(?:oice)?\s*(?:no|num|number|#)"
            r"|document\s*(?:no|num|number)"
            r"|note\s*(?:no|num|number)"
            r"|voucher\s*(?:no|num|number)"
            r"|bill\s*(?:no|num|number)"
            r"|inv(?:oice)?\s*(?:ref)",
            re.IGNORECASE,
        ),
        "Invoice Date": re.compile(
            r"inv(?:oice)?\s*(?:date|dt)"
            r"|document\s*(?:date|dt)"
            r"|note\s*(?:date|dt)"
            r"|voucher\s*(?:date|dt)"
            r"|bill\s*(?:date|dt)",
            re.IGNORECASE,
        ),
        "Taxable Value": re.compile(
            r"taxable\s*(?:val|value|amt|amount)"
            r"|assessable\s*(?:val|value|amt|amount)"
            r"|base\s*(?:val|value|amt|amount)",
            re.IGNORECASE,
        ),
        "IGST": re.compile(
            r"\bigst\b|integrated\s*tax|integrated\s*gst",
            re.IGNORECASE,
        ),
        "CGST": re.compile(
            r"\bcgst\b|central\s*tax|central\s*gst",
            re.IGNORECASE,
        ),
        "SGST": re.compile(
            r"\bsgst\b|\butgst\b|state\s*tax|state\s*gst|sgst\s*/\s*utgst",
            re.IGNORECASE,
        ),
    }

    # ------- pass 1: exact (case-insensitive) match -------
    mapping = {}
    used_cols = set()

    for req in required_cols:
        for col in df_columns:
            if col in used_cols:
                continue
            if col.strip().lower() == req.lower():
                mapping[col] = req
                used_cols.add(col)
                break

    # ------- pass 2: regex match on remaining fields -------
    for req in required_cols:
        if req in mapping.values():
            continue
        pat = _PATTERNS.get(req)
        if pat is None:
            continue
        for col in df_columns:
            if col in used_cols:
                continue
            if pat.search(col):
                mapping[col] = req
                used_cols.add(col)
                break

    return mapping


# ---------------------------------------------------------------------------
# Input — File readers
# ---------------------------------------------------------------------------

def read_books_file(file_or_path):
    """Read a Books purchase-register Excel file and return a cleaned DataFrame."""
    df = pd.read_excel(file_or_path)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def read_2b_file(file_or_path):
    """Read a GSTR-2B Excel file with smart B2B-sheet and multi-row-header detection."""
    try:
        xls = pd.ExcelFile(file_or_path)
        target_sheet = None
        for sheet in xls.sheet_names:
            if str(sheet).strip().upper() == "B2B":
                target_sheet = sheet
                break

        if target_sheet:
            df_raw = pd.read_excel(xls, sheet_name=target_sheet, header=None)
        else:
            df_raw = pd.read_excel(file_or_path, header=None)
    except Exception:
        df_raw = pd.read_excel(file_or_path, header=None)

    # Detect the header row
    header_idx = 0
    for idx in range(min(15, len(df_raw))):
        try:
            row_values = df_raw.iloc[idx].dropna().astype(str).str.lower()
            row_str = " ".join(row_values)
            if 'gstin' in row_str and (
                'invoice' in row_str or 'inv' in row_str or
                'name' in row_str or 'party' in row_str or 'date' in row_str
            ):
                header_idx = idx
                break
        except Exception:
            break

    # Check for multi-row headers
    is_multi_row = False
    if header_idx + 1 < len(df_raw):
        row2_str = " ".join(
            df_raw.iloc[header_idx + 1].dropna().astype(str).str.lower()
        )
        if any(kw in row2_str for kw in [
            'taxable', 'integrated', 'central', 'sgst', 'igst', 'cgst', 'rate'
        ]):
            is_multi_row = True

    if is_multi_row:
        row1 = df_raw.iloc[header_idx].ffill().fillna('')
        row2 = df_raw.iloc[header_idx + 1].fillna('')
        cols = []
        for c1, c2 in zip(row1, row2):
            c1, c2 = str(c1).strip(), str(c2).strip()
            if c1 and c2 and c1 != c2:
                cols.append(f"{c1} - {c2}")
            elif c1:
                cols.append(c1)
            elif c2:
                cols.append(c2)
            else:
                cols.append("Unnamed")
        df = df_raw.iloc[header_idx + 2:].copy()
        df.columns = cols
        df.reset_index(drop=True, inplace=True)
    else:
        df = df_raw.iloc[header_idx + 1:].copy()
        df.columns = df_raw.iloc[header_idx].fillna('Unnamed').astype(str)
        df.reset_index(drop=True, inplace=True)

    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how='all')
    return df


# ---------------------------------------------------------------------------
# Core — Reconciliation engine
# ---------------------------------------------------------------------------

def process_reconciliation(df_books, df_2b, b_map, t_map, progress_callback=None):
    """Run the fuzzy-matching reconciliation between Books and GSTR-2B data.

    Parameters
    ----------
    df_books : DataFrame  – purchase register data.
    df_2b    : DataFrame  – GSTR-2B data.
    b_map    : dict       – {original_col: standard_col} for books.
    t_map    : dict       – {original_col: standard_col} for 2B.
    progress_callback : callable, optional
        Called with (current_index, total) so the caller can update a UI
        progress bar.  Not required.

    Returns
    -------
    (df_matched, df_books_unmatched, df_2b_unmatched)
    """
    df_books = df_books.copy()
    df_2b = df_2b.copy()

    # Avoid accidental column collisions before renaming
    for col in list(df_books.columns):
        if col in b_map.values() and col not in b_map.keys():
            df_books = df_books.rename(columns={col: f"{col}_original"})

    for col in list(df_2b.columns):
        if col in t_map.values() and col not in t_map.keys():
            df_2b = df_2b.rename(columns={col: f"{col}_original"})

    # Normalize headers
    df_books = df_books.rename(columns=b_map)
    df_2b = df_2b.rename(columns=t_map)

    deduplicate_columns(df_books)
    deduplicate_columns(df_2b)

    # Ensure required columns exist
    for col in ["GSTIN", "Party Name", "Invoice No"]:
        if col not in df_books.columns:
            df_books[col] = ""
        if col not in df_2b.columns:
            df_2b[col] = ""

    if "Invoice Date" not in df_books.columns:
        df_books["Invoice Date"] = np.nan
    if "Invoice Date" not in df_2b.columns:
        df_2b["Invoice Date"] = np.nan

    # Clean GSTIN
    df_books['GSTIN'] = df_books['GSTIN'].astype(str).str.strip().str.upper().replace('NAN', '')
    df_2b['GSTIN'] = df_2b['GSTIN'].astype(str).str.strip().str.upper().replace('NAN', '')

    # Clean invoice numbers
    df_books['Clean_Inv'] = df_books['Invoice No'].apply(clean_inv)
    df_2b['Clean_Inv'] = df_2b['Invoice No'].apply(clean_inv)

    # Parse dates
    df_books['Invoice Date'] = pd.to_datetime(df_books['Invoice Date'], errors='coerce')
    df_2b['Invoice Date'] = pd.to_datetime(df_2b['Invoice Date'], errors='coerce')

    # Parse financials
    for c in ['Taxable Value', 'CGST', 'SGST', 'IGST']:
        if c not in df_books.columns:
            df_books[c] = 0
        if c not in df_2b.columns:
            df_2b[c] = 0
        df_books[c] = pd.to_numeric(df_books[c], errors='coerce').fillna(0)
        df_2b[c] = pd.to_numeric(df_2b[c], errors='coerce').fillna(0)

    df_books['TotalTax'] = df_books['CGST'] + df_books['SGST'] + df_books['IGST']
    df_2b['TotalTax'] = df_2b['CGST'] + df_2b['SGST'] + df_2b['IGST']

    matched_records = []
    books_unmatched = []
    t2b_unmatched = []

    df_books_enum = df_books.copy().reset_index()
    df_2b_enum = df_2b.copy().reset_index()

    all_gstins = list(
        set(df_books_enum['GSTIN'].unique()) | set(df_2b_enum['GSTIN'].unique())
    )
    total = len(all_gstins)

    for i, gstin in enumerate(all_gstins):
        if progress_callback and i % 10 == 0:
            progress_callback(i, total)

        b_subset = df_books_enum[df_books_enum['GSTIN'] == gstin]
        t_subset = df_2b_enum[df_2b_enum['GSTIN'] == gstin]

        if b_subset.empty:
            for _, row in t_subset.iterrows():
                t2b_unmatched.append(row)
            continue
        if t_subset.empty:
            for _, row in b_subset.iterrows():
                books_unmatched.append(row)
            continue

        # Score every possible pair within this GSTIN
        possible_matches = []
        for _, b_row in b_subset.iterrows():
            b_inv = b_row['Clean_Inv']
            b_taxable = b_row['Taxable Value']
            b_tax = b_row['TotalTax']
            b_date = b_row['Invoice Date']
            has_inv = bool(b_inv)

            for _, t_row in t_subset.iterrows():
                t_inv = t_row['Clean_Inv']
                t_taxable = t_row['Taxable Value']
                t_tax = t_row['TotalTax']
                t_date = t_row['Invoice Date']

                inv_sim = fuzz.ratio(b_inv, t_inv) if has_inv and t_inv else 0
                taxable_sim = 1 - abs(b_taxable - t_taxable) / (b_taxable + 1)
                tax_sim = 1 - abs(b_tax - t_tax) / (b_tax + 1)

                date_score = 0
                if pd.notna(b_date) and pd.notna(t_date):
                    if abs((b_date - t_date).days) <= 5:
                        date_score = 1

                if has_inv:
                    score = (
                        (inv_sim / 100 * 40)
                        + (taxable_sim * 30)
                        + (tax_sim * 20)
                        + (date_score * 10)
                    )
                else:
                    score = (
                        (taxable_sim * 30)
                        + (tax_sim * 20)
                        + (date_score * 10)
                    )

                possible_matches.append((score, b_row, t_row, has_inv))

        possible_matches.sort(key=lambda x: x[0], reverse=True)
        b_used = set()
        t_used = set()

        for score, b_row, t_row, has_inv in possible_matches:
            if b_row['index'] in b_used or t_row['index'] in t_used:
                continue

            # Classification
            if has_inv:
                if score >= 90:
                    cat = "Exact Match"
                elif score >= 70:
                    cat = "Probable Match"
                else:
                    cat = "Exception"
            else:
                if score >= 55:
                    cat = "Most Likely Match"
                elif score >= 40:
                    cat = "Probable Match"
                else:
                    cat = "Exception"

            tax_diff = b_row['TotalTax'] - t_row['TotalTax']
            matched_records.append({
                'GSTIN': gstin,
                'Party Name': b_row['Party Name'],
                'Books Invoice No.': b_row['Invoice No'],
                '2B Invoice No.': t_row['Invoice No'],
                'Match Score': round(score, 2),
                'Taxable Amt.': b_row['Taxable Value'],
                'CGST': b_row['CGST'],
                'SGST': b_row['SGST'],
                'IGST': b_row['IGST'],
                'Total Tax': b_row['TotalTax'],
                '2B Taxable Amt.': t_row['Taxable Value'],
                '2B CGST': t_row['CGST'],
                '2B SGST': t_row['SGST'],
                '2B IGST': t_row['IGST'],
                '2B Total Tax': t_row['TotalTax'],
                'Tax Diff': tax_diff,
                'Category': cat,
            })
            b_used.add(b_row['index'])
            t_used.add(t_row['index'])

        for _, b_row in b_subset.iterrows():
            if b_row['index'] not in b_used:
                books_unmatched.append(b_row)
        for _, t_row in t_subset.iterrows():
            if t_row['index'] not in t_used:
                t2b_unmatched.append(t_row)

    # Build result DataFrames
    df_matched = pd.DataFrame(matched_records)
    if df_matched.empty:
        df_matched = pd.DataFrame(columns=[
            'GSTIN', 'Party Name', 'Books Invoice No.', '2B Invoice No.',
            'Match Score', 'Taxable Amt.', 'CGST', 'SGST', 'IGST',
            'Total Tax', '2B Taxable Amt.', '2B CGST', '2B SGST',
            '2B IGST', '2B Total Tax', 'Tax Diff', 'Category',
        ])

    df_books_un = pd.DataFrame(books_unmatched)
    if 'index' in df_books_un.columns:
        df_books_un = df_books_un.drop(columns=['index', 'Clean_Inv', 'TotalTax'])
    df_2b_un = pd.DataFrame(t2b_unmatched)
    if 'index' in df_2b_un.columns:
        df_2b_un = df_2b_un.drop(columns=['index', 'Clean_Inv', 'TotalTax'])

    return df_matched, df_books_un, df_2b_un


# ---------------------------------------------------------------------------
# Output — Metrics computation
# ---------------------------------------------------------------------------

def compute_summary_metrics(matched, un_books, un_2b, books_df, t2b_df,
                            books_mapping, t2b_mapping):
    """Compute the high-level reconciliation dashboard numbers.

    Returns a dict with keys:
        books_total_itc, t2b_total_itc, matched_itc,
        books_risk_itc, t2b_risk_itc,
        books_invoice_count, t2b_invoice_count,
        matched_count, un_books_count, un_2b_count
    """
    b_total_itc = get_mapped_sum(books_df, books_mapping, ['CGST', 'SGST', 'IGST'])
    t_total_itc = get_mapped_sum(t2b_df, t2b_mapping, ['CGST', 'SGST', 'IGST'])

    matched_itc = safe_sum(matched, 'Total Tax')
    books_risk_itc = (
        sum(safe_sum(un_books, v) for v in ['CGST', 'SGST', 'IGST'])
        if not un_books.empty else 0
    )
    t2b_risk_itc = (
        sum(safe_sum(un_2b, v) for v in ['CGST', 'SGST', 'IGST'])
        if not un_2b.empty else 0
    )

    return {
        'books_total_itc': b_total_itc,
        't2b_total_itc': t_total_itc,
        'matched_itc': matched_itc,
        'books_risk_itc': books_risk_itc,
        't2b_risk_itc': t2b_risk_itc,
        'books_invoice_count': len(books_df),
        't2b_invoice_count': len(t2b_df),
        'matched_count': len(matched),
        'un_books_count': len(un_books),
        'un_2b_count': len(un_2b),
    }


# ---------------------------------------------------------------------------
# Output — Excel export
# ---------------------------------------------------------------------------

def _get_col_letter(col_idx):
    """Convert a 0-based column index to an Excel column letter (A, B, … AA, AB …)."""
    res = ""
    while col_idx >= 0:
        res = chr((col_idx % 26) + 65) + res
        col_idx = (col_idx // 26) - 1
    return res


def _get_total_cell(sheet_name, df, col_name):
    """Return an Excel cell reference pointing to the Grand Total row for *col_name*."""
    if df.empty or col_name not in df.columns:
        return "0"
    col_idx = df.columns.get_loc(col_name)
    if isinstance(col_idx, np.ndarray):
        col_idx = col_idx[0]
    letter = _get_col_letter(col_idx)
    return f"'{sheet_name}'!{letter}{len(df) + 2}"


def _write_df_to_sheet(workbook, sheet_name, df, formats):
    """Write *df* into a new worksheet inside *workbook* with formatting."""
    sheet = workbook.add_worksheet(sheet_name)
    if df.empty:
        return

    fmt_num = formats['num']
    fmt_date = formats['date']
    fmt_head = formats['head']
    fmt_text = formats['text']
    fmt_total_text = formats['total_text']
    fmt_total_num = formats['total_num']

    is_data_sheet = sheet_name not in ["Summary"]
    if is_data_sheet:
        df = df.copy()
        total_row = {col: "" for col in df.columns}
        if len(df.columns) > 0:
            total_row[df.columns[0]] = "Grand Total"
        for col_idx, col in enumerate(df.columns):
            col_str = str(col).upper()
            if any(kw in col_str for kw in ['TAXABLE', 'CGST', 'SGST', 'IGST', 'TAX', 'CESS']):
                if 'INV' not in col_str and 'RATE' not in col_str:
                    letter = _get_col_letter(col_idx)
                    total_row[col] = f"=SUM({letter}2:{letter}{len(df) + 1})"
        df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

    df = df.fillna("")

    for col_num, value in enumerate(df.columns.values):
        sheet.write(0, col_num, value, fmt_head)

    for row_num, row_data in enumerate(df.values):
        is_total_row = is_data_sheet and row_num == len(df) - 1
        for col_num, val in enumerate(row_data):
            col_name = df.columns[col_num]
            if str(val).startswith('='):
                sheet.write_formula(
                    row_num + 1, col_num, str(val),
                    fmt_total_num if is_total_row else fmt_num,
                )
            elif "date" in str(col_name).lower() and val != "" and not is_total_row:
                try:
                    if pd.notna(val):
                        sheet.write_datetime(
                            row_num + 1, col_num,
                            pd.to_datetime(val), fmt_date,
                        )
                    else:
                        sheet.write(row_num + 1, col_num, val, fmt_text)
                except Exception:
                    sheet.write(row_num + 1, col_num, str(val), fmt_text)
            elif isinstance(val, (int, float)) and pd.notna(val):
                sheet.write_number(
                    row_num + 1, col_num, val,
                    fmt_total_num if is_total_row else fmt_num,
                )
            else:
                is_heading = (val == col_name) and (row_num > 0)
                f = (
                    fmt_head if is_heading
                    else fmt_total_text if is_total_row
                    else fmt_text
                )
                sheet.write(row_num + 1, col_num, str(val), f)

    # Auto-fit columns (simple approximation)
    for col_num, col_name in enumerate(df.columns.values):
        max_len = max(
            [len(str(val)) for val in df.iloc[:, col_num].values]
            + [len(str(col_name))]
        ) + 2
        sheet.set_column(col_num, col_num, max_len)


def export_to_excel(matched, un_books, un_2b,
                    books_df, t2b_df, books_mapping, t2b_mapping):
    """Generate the full reconciliation Excel report and return it as bytes.

    Parameters
    ----------
    matched      : DataFrame – matched records from process_reconciliation.
    un_books     : DataFrame – books records not found in 2B.
    un_2b        : DataFrame – 2B records not found in books.
    books_df     : DataFrame – original uploaded books data.
    t2b_df       : DataFrame – original uploaded 2B data.
    books_mapping: dict      – column mapping used for books.
    t2b_mapping  : dict      – column mapping used for 2B.

    Returns
    -------
    bytes – the Excel file content ready to be written to disk or streamed.
    """
    tc = len  # shorthand

    b_total_itc = get_mapped_sum(books_df, books_mapping, ['CGST', 'SGST', 'IGST'])
    t_total_itc = get_mapped_sum(t2b_df, t2b_mapping, ['CGST', 'SGST', 'IGST'])

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    formats = {
        'num': workbook.add_format({'num_format': '#,##,##0.00'}),
        'date': workbook.add_format({'num_format': 'dd-mm-yyyy'}),
        'head': workbook.add_format({'bold': True, 'bg_color': '#E0E0E0', 'border': 1}),
        'text': workbook.add_format({}),
        'total_text': workbook.add_format({'bold': True, 'bg_color': '#FFFFCC', 'border': 1}),
        'total_num': workbook.add_format({
            'num_format': '#,##,##0.00', 'bold': True,
            'bg_color': '#FFFFCC', 'border': 1,
        }),
    }

    # ---- Summary sheet data ----
    summary_data = {
        "Position / Category": [
            "Total Uploaded - Books Data",
            "Total Uploaded - GSTR 2B Data",
            "Matched (Available in both)",
            "Books records Not in 2B (Books Risk)",
            "2B records Not in Books (2B Risk)",
        ],
        "Invoice Count": [
            tc(books_df),
            tc(t2b_df),
            f"=COUNTA('Matched'!A2:A{max(2, tc(matched) + 1)})" if not matched.empty else 0,
            f"=COUNTA('Books_Not_in_2B'!A2:A{max(2, tc(un_books) + 1)})" if not un_books.empty else 0,
            f"=COUNTA('2B_Not_in_Books'!A2:A{max(2, tc(un_2b) + 1)})" if not un_2b.empty else 0,
        ],
        "Taxable Value": [
            get_mapped_sum(books_df, books_mapping, ['Taxable Value']),
            get_mapped_sum(t2b_df, t2b_mapping, ['Taxable Value']),
            f"={_get_total_cell('Matched', matched, 'Taxable Amt.')}",
            f"={_get_total_cell('Books_Not_in_2B', un_books, 'Taxable Value')}",
            f"={_get_total_cell('2B_Not_in_Books', un_2b, 'Taxable Value')}",
        ],
        "IGST": [
            get_mapped_sum(books_df, books_mapping, ['IGST']),
            get_mapped_sum(t2b_df, t2b_mapping, ['IGST']),
            f"={_get_total_cell('Matched', matched, 'IGST')}",
            f"={_get_total_cell('Books_Not_in_2B', un_books, 'IGST')}",
            f"={_get_total_cell('2B_Not_in_Books', un_2b, 'IGST')}",
        ],
        "CGST": [
            get_mapped_sum(books_df, books_mapping, ['CGST']),
            get_mapped_sum(t2b_df, t2b_mapping, ['CGST']),
            f"={_get_total_cell('Matched', matched, 'CGST')}",
            f"={_get_total_cell('Books_Not_in_2B', un_books, 'CGST')}",
            f"={_get_total_cell('2B_Not_in_Books', un_2b, 'CGST')}",
        ],
        "SGST": [
            get_mapped_sum(books_df, books_mapping, ['SGST']),
            get_mapped_sum(t2b_df, t2b_mapping, ['SGST']),
            f"={_get_total_cell('Matched', matched, 'SGST')}",
            f"={_get_total_cell('Books_Not_in_2B', un_books, 'SGST')}",
            f"={_get_total_cell('2B_Not_in_Books', un_2b, 'SGST')}",
        ],
        "Total Tax Amount": [
            b_total_itc,
            t_total_itc,
            f"={_get_total_cell('Matched', matched, 'Total Tax')}",
            "=D5+E5+F5",
            "=D6+E6+F6",
        ],
    }
    df_summary = pd.DataFrame(summary_data)

    # ---- Cross-check section ----
    cross_check_data = {
        "Position / Category": [
            "",
            "Position / Category",
            "[CROSS CHECK] 1. Books Validation",
            "   -> Total from Uploaded Books",
            "   -> Accounted For (Matched + Books Not in 2B)",
            "   -> Books Variance (Difference)",
            "",
            "[CROSS CHECK] 2. GSTR-2B Validation",
            "   -> Total from Uploaded GSTR 2B",
            "   -> Accounted For (Matched 2B values + 2B Not in Books)",
            "   -> 2B Variance (Difference)",
        ],
        "Invoice Count": [
            "", "Invoice Count",
            "", "=B2", "=B4+B5", "=B10-B11",
            "",
            "", "=B3", "=B4+B6", "=B15-B16",
        ],
        "Taxable Value": [
            "", "Taxable Value",
            "", "=C2", "=C4+C5", "=C10-C11",
            "",
            "", "=C3",
            f"={_get_total_cell('Matched', matched, '2B Taxable Amt.')} + C6",
            "=C15-C16",
        ],
        "IGST": [
            "", "IGST",
            "", "=D2", "=D4+D5", "=D10-D11",
            "",
            "", "=D3",
            f"={_get_total_cell('Matched', matched, '2B IGST')} + D6",
            "=D15-D16",
        ],
        "CGST": [
            "", "CGST",
            "", "=E2", "=E4+E5", "=E10-E11",
            "",
            "", "=E3",
            f"={_get_total_cell('Matched', matched, '2B CGST')} + E6",
            "=E15-E16",
        ],
        "SGST": [
            "", "SGST",
            "", "=F2", "=F4+F5", "=F10-F11",
            "",
            "", "=F3",
            f"={_get_total_cell('Matched', matched, '2B SGST')} + F6",
            "=F15-F16",
        ],
        "Total Tax Amount": [
            "", "Total Tax Amount",
            "", "=G2", "=G4+G5", "=G10-G11",
            "",
            "", "=G3",
            f"={_get_total_cell('Matched', matched, '2B Total Tax')} + G6",
            "=G15-G16",
        ],
    }
    df_cross_check = pd.DataFrame(cross_check_data)
    df_combined = pd.concat([df_summary, df_cross_check], ignore_index=True)

    # ---- Write sheets ----
    _write_df_to_sheet(workbook, "Summary", df_combined, formats)
    _write_df_to_sheet(workbook, "Matched", matched, formats)
    _write_df_to_sheet(workbook, "Books_Not_in_2B", un_books, formats)
    _write_df_to_sheet(workbook, "2B_Not_in_Books", un_2b, formats)

    workbook.close()
    return output.getvalue()


# ---------------------------------------------------------------------------
# 2B DB records → DataFrame converter
# ---------------------------------------------------------------------------

def convert_2b_records_to_df(records: list[dict]) -> pd.DataFrame:
    """Convert B2B records from the Gstr2B.records JSONB column into the
    standard DataFrame format expected by ``process_reconciliation``.

    Each record dict has keys like supplier_gstin, supplier_name,
    invoice_number, invoice_date, taxable_value, cgst, sgst, igst produced
    by ``_parse_b2b_section`` in the 2B service.
    """
    if not records:
        return pd.DataFrame(columns=[
            "GSTIN", "Party Name", "Invoice No", "Invoice Date",
            "Taxable Value", "CGST", "SGST", "IGST",
        ])

    rows = []
    for r in records:
        rows.append({
            "GSTIN": r.get("supplier_gstin", ""),
            "Party Name": r.get("supplier_name", ""),
            "Invoice No": r.get("invoice_number", ""),
            "Invoice Date": r.get("invoice_date", ""),
            "Taxable Value": r.get("taxable_value", 0),
            "CGST": r.get("cgst", 0),
            "SGST": r.get("sgst", 0),
            "IGST": r.get("igst", 0),
        })

    df = pd.DataFrame(rows)
    for col in ["Taxable Value", "CGST", "SGST", "IGST"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


# ---------------------------------------------------------------------------
# CDNR DB records → DataFrame converter
# ---------------------------------------------------------------------------

def convert_cdnr_records_to_df(records: list[dict]) -> pd.DataFrame:
    """Convert CDNR/CDNRA records from Gstr2B.records into the standard
    DataFrame format expected by ``process_reconciliation``.

    CDNR records have ``note_number`` / ``note_date`` instead of
    ``invoice_number`` / ``invoice_date``.  Credit notes (note_type='C')
    get negative tax values so that ITC reduction is reflected correctly
    in summaries.
    """
    if not records:
        return pd.DataFrame(columns=[
            "GSTIN", "Party Name", "Invoice No", "Invoice Date",
            "Taxable Value", "CGST", "SGST", "IGST", "Note Type",
        ])

    rows = []
    for r in records:
        note_type = r.get("note_type", "D")  # C = Credit, D = Debit
        sign = -1 if note_type == "C" else 1

        rows.append({
            "GSTIN": r.get("supplier_gstin", ""),
            "Party Name": r.get("supplier_name", ""),
            "Invoice No": r.get("note_number", ""),
            "Invoice Date": r.get("note_date", ""),
            "Taxable Value": (r.get("taxable_value", 0) or 0) * sign,
            "CGST": (r.get("cgst", 0) or 0) * sign,
            "SGST": (r.get("sgst", 0) or 0) * sign,
            "IGST": (r.get("igst", 0) or 0) * sign,
            "Note Type": note_type,
        })

    df = pd.DataFrame(rows)
    for col in ["Taxable Value", "CGST", "SGST", "IGST"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


# ---------------------------------------------------------------------------
# HTML report generator
# ---------------------------------------------------------------------------

def generate_html_report(matched_df, un_books_df, un_2b_df, metrics: dict) -> str:
    """Return a self-contained HTML report string for download."""

    def _fmt(v):
        try:
            return f"{float(v):,.2f}"
        except (ValueError, TypeError):
            return str(v) if v is not None else "—"

    def _df_to_html_rows(df):
        if df.empty:
            return "<tr><td colspan='100%' style='text-align:center;padding:12px;color:#888;'>No records</td></tr>"
        rows = []
        for _, row in df.iterrows():
            cells = "".join(f"<td>{_fmt(v) if isinstance(v, (int, float)) else (v if pd.notna(v) else '—')}</td>" for v in row)
            rows.append(f"<tr>{cells}</tr>")
        return "\n".join(rows)

    def _df_to_table(df, title):
        if df.empty:
            headers = ""
        else:
            headers = "".join(f"<th>{c}</th>" for c in df.columns)
        return f"""
        <h2 style="margin-top:30px;">{title}</h2>
        <div style="overflow-x:auto;">
        <table>
          <thead><tr>{headers}</tr></thead>
          <tbody>{_df_to_html_rows(df)}</tbody>
        </table>
        </div>"""

    # Category-based row coloring for matched table
    def _matched_table(df):
        if df.empty:
            return _df_to_table(df, "Matched Records")
        headers = "".join(f"<th>{c}</th>" for c in df.columns)
        rows = []
        for _, row in df.iterrows():
            cat = row.get("Category", "")
            if cat == "Exact Match":
                bg = "#d4edda"
            elif cat in ("Probable Match", "Most Likely Match"):
                bg = "#fff3cd"
            else:
                bg = "#f8d7da"
            cells = "".join(
                f"<td>{_fmt(v) if isinstance(v, (int, float)) else (v if pd.notna(v) else '—')}</td>"
                for v in row
            )
            rows.append(f"<tr style='background:{bg};'>{cells}</tr>")
        return f"""
        <h2 style="margin-top:30px;">Matched Records</h2>
        <div style="overflow-x:auto;">
        <table>
          <thead><tr>{headers}</tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GSTR-2B Reconciliation Report</title>
<style>
  body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background: #f9f9f9; color: #333; }}
  h1 {{ color: #1a237e; border-bottom: 2px solid #1a237e; padding-bottom: 8px; }}
  .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin: 20px 0; }}
  .metric-card {{ background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .metric-card .label {{ font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }}
  .metric-card .value {{ font-size: 22px; font-weight: 700; margin-top: 4px; color: #1a237e; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; background: #fff; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; white-space: nowrap; }}
  th {{ background: #e0e0e0; font-weight: 600; position: sticky; top: 0; }}
  tr:nth-child(even) {{ background: #fafafa; }}
</style></head><body>
<h1>GSTR-2B Reconciliation Report</h1>
<div class="metrics">
  <div class="metric-card"><div class="label">Books Total ITC</div><div class="value">{_fmt(metrics.get('books_total_itc', 0))}</div></div>
  <div class="metric-card"><div class="label">2B Total ITC</div><div class="value">{_fmt(metrics.get('t2b_total_itc', 0))}</div></div>
  <div class="metric-card"><div class="label">Matched ITC</div><div class="value">{_fmt(metrics.get('matched_itc', 0))}</div></div>
  <div class="metric-card"><div class="label">Books Risk ITC</div><div class="value">{_fmt(metrics.get('books_risk_itc', 0))}</div></div>
  <div class="metric-card"><div class="label">2B Risk ITC</div><div class="value">{_fmt(metrics.get('t2b_risk_itc', 0))}</div></div>
  <div class="metric-card"><div class="label">Matched Count</div><div class="value">{metrics.get('matched_count', 0)}</div></div>
  <div class="metric-card"><div class="label">Books Invoices</div><div class="value">{metrics.get('books_invoice_count', 0)}</div></div>
  <div class="metric-card"><div class="label">2B Invoices</div><div class="value">{metrics.get('t2b_invoice_count', 0)}</div></div>
  <div class="metric-card"><div class="label">Books Not in 2B</div><div class="value">{metrics.get('un_books_count', 0)}</div></div>
  <div class="metric-card"><div class="label">2B Not in Books</div><div class="value">{metrics.get('un_2b_count', 0)}</div></div>
</div>
{_matched_table(matched_df)}
{_df_to_table(un_books_df, "Books Not in 2B")}
{_df_to_table(un_2b_df, "2B Not in Books")}
</body></html>"""
    return html


# ---------------------------------------------------------------------------
# Combined Excel export (B2B + CDNR)
# ---------------------------------------------------------------------------

def export_to_excel_combined(
    b2b_matched, b2b_un_books, b2b_un_2b,
    b2b_books_df, b2b_t2b_df, b2b_books_mapping, b2b_t2b_mapping,
    cdnr_matched, cdnr_un_books, cdnr_un_2b,
    cdnr_books_df, cdnr_t2b_df, cdnr_books_mapping, cdnr_t2b_mapping,
):
    """Generate the full reconciliation Excel with B2B and CDNR sheets."""

    tc = len

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    formats = {
        'num': workbook.add_format({'num_format': '#,##,##0.00'}),
        'date': workbook.add_format({'num_format': 'dd-mm-yyyy'}),
        'head': workbook.add_format({'bold': True, 'bg_color': '#E0E0E0', 'border': 1}),
        'text': workbook.add_format({}),
        'total_text': workbook.add_format({'bold': True, 'bg_color': '#FFFFCC', 'border': 1}),
        'total_num': workbook.add_format({
            'num_format': '#,##,##0.00', 'bold': True,
            'bg_color': '#FFFFCC', 'border': 1,
        }),
        'section_head': workbook.add_format({
            'bold': True, 'bg_color': '#C5CAE9', 'border': 1, 'font_size': 12,
        }),
    }

    # ---- B2B Summary (formula-driven, mirrors the Streamlit app) ----
    b_total = get_mapped_sum(b2b_books_df, b2b_books_mapping, ['CGST', 'SGST', 'IGST'])
    t_total = get_mapped_sum(b2b_t2b_df, b2b_t2b_mapping, ['CGST', 'SGST', 'IGST'])

    summary_rows = [
        ["B2B RECONCILIATION", "", "", "", "", "", ""],
        ["Position / Category", "Invoice Count", "Taxable Value", "IGST", "CGST", "SGST", "Total Tax Amount"],
        [
            "Total Uploaded - Books Data", tc(b2b_books_df),
            get_mapped_sum(b2b_books_df, b2b_books_mapping, ['Taxable Value']),
            get_mapped_sum(b2b_books_df, b2b_books_mapping, ['IGST']),
            get_mapped_sum(b2b_books_df, b2b_books_mapping, ['CGST']),
            get_mapped_sum(b2b_books_df, b2b_books_mapping, ['SGST']),
            b_total,
        ],
        [
            "Total Uploaded - GSTR 2B (B2B)", tc(b2b_t2b_df),
            get_mapped_sum(b2b_t2b_df, b2b_t2b_mapping, ['Taxable Value']),
            get_mapped_sum(b2b_t2b_df, b2b_t2b_mapping, ['IGST']),
            get_mapped_sum(b2b_t2b_df, b2b_t2b_mapping, ['CGST']),
            get_mapped_sum(b2b_t2b_df, b2b_t2b_mapping, ['SGST']),
            t_total,
        ],
        [
            "Matched (B2B)",
            f"=COUNTA('B2B_Matched'!A2:A{max(2, tc(b2b_matched) + 1)})" if not b2b_matched.empty else 0,
            f"={_get_total_cell('B2B_Matched', b2b_matched, 'Taxable Amt.')}",
            f"={_get_total_cell('B2B_Matched', b2b_matched, 'IGST')}",
            f"={_get_total_cell('B2B_Matched', b2b_matched, 'CGST')}",
            f"={_get_total_cell('B2B_Matched', b2b_matched, 'SGST')}",
            f"={_get_total_cell('B2B_Matched', b2b_matched, 'Total Tax')}",
        ],
        [
            "Books Not in 2B (B2B)",
            f"=COUNTA('B2B_Books_Not_in_2B'!A2:A{max(2, tc(b2b_un_books) + 1)})" if not b2b_un_books.empty else 0,
            f"={_get_total_cell('B2B_Books_Not_in_2B', b2b_un_books, 'Taxable Value')}",
            f"={_get_total_cell('B2B_Books_Not_in_2B', b2b_un_books, 'IGST')}",
            f"={_get_total_cell('B2B_Books_Not_in_2B', b2b_un_books, 'CGST')}",
            f"={_get_total_cell('B2B_Books_Not_in_2B', b2b_un_books, 'SGST')}",
            "=D7+E7+F7",
        ],
        [
            "2B Not in Books (B2B)",
            f"=COUNTA('B2B_2B_Not_in_Books'!A2:A{max(2, tc(b2b_un_2b) + 1)})" if not b2b_un_2b.empty else 0,
            f"={_get_total_cell('B2B_2B_Not_in_Books', b2b_un_2b, 'Taxable Value')}",
            f"={_get_total_cell('B2B_2B_Not_in_Books', b2b_un_2b, 'IGST')}",
            f"={_get_total_cell('B2B_2B_Not_in_Books', b2b_un_2b, 'CGST')}",
            f"={_get_total_cell('B2B_2B_Not_in_Books', b2b_un_2b, 'SGST')}",
            "=D8+E8+F8",
        ],
    ]

    # ---- B2B Cross-check ----
    summary_rows += [
        [],
        ["", "", "", "", "", "", ""],
        ["", "Invoice Count", "Taxable Value", "IGST", "CGST", "SGST", "Total Tax Amount"],
        ["[B2B CROSS CHECK] 1. Books Validation", "", "", "", "", "", ""],
        ["   -> Total from Uploaded Books", "=B3", "=C3", "=D3", "=E3", "=F3", "=G3"],
        ["   -> Accounted For (Matched + Books Not in 2B)", "=B6+B7", "=C6+C7", "=D6+D7", "=E6+E7", "=F6+F7", "=G6+G7"],
        ["   -> Books Variance (Difference)", "=B13-B14", "=C13-C14", "=D13-D14", "=E13-E14", "=F13-F14", "=G13-G14"],
        [],
        ["[B2B CROSS CHECK] 2. GSTR-2B Validation", "", "", "", "", "", ""],
        ["   -> Total from Uploaded GSTR 2B", "=B4", "=C4", "=D4", "=E4", "=F4", "=G4"],
        [
            "   -> Accounted For (Matched 2B values + 2B Not in Books)",
            "=B6+B8",
            f"={_get_total_cell('B2B_Matched', b2b_matched, '2B Taxable Amt.')} + C8",
            f"={_get_total_cell('B2B_Matched', b2b_matched, '2B IGST')} + D8",
            f"={_get_total_cell('B2B_Matched', b2b_matched, '2B CGST')} + E8",
            f"={_get_total_cell('B2B_Matched', b2b_matched, '2B SGST')} + F8",
            f"={_get_total_cell('B2B_Matched', b2b_matched, '2B Total Tax')} + G8",
        ],
        ["   -> 2B Variance (Difference)", "=B18-B19", "=C18-C19", "=D18-D19", "=E18-E19", "=F18-F19", "=G18-G19"],
    ]

    # ---- CDNR Summary ----
    cn_b_total = get_mapped_sum(cdnr_books_df, cdnr_books_mapping, ['CGST', 'SGST', 'IGST']) if not cdnr_t2b_df.empty else 0
    cn_t_total = get_mapped_sum(cdnr_t2b_df, cdnr_t2b_mapping, ['CGST', 'SGST', 'IGST']) if not cdnr_t2b_df.empty else 0

    # Row 22 onwards (0-indexed in the list, but row 22+ in Excel after header)
    summary_rows += [
        [],
        ["CDNR RECONCILIATION", "", "", "", "", "", ""],
        ["Position / Category", "Note Count", "Taxable Value", "IGST", "CGST", "SGST", "Total Tax Amount"],
        [
            "Total GSTR 2B (CDNR)", tc(cdnr_t2b_df),
            get_mapped_sum(cdnr_t2b_df, cdnr_t2b_mapping, ['Taxable Value']) if not cdnr_t2b_df.empty else 0,
            get_mapped_sum(cdnr_t2b_df, cdnr_t2b_mapping, ['IGST']) if not cdnr_t2b_df.empty else 0,
            get_mapped_sum(cdnr_t2b_df, cdnr_t2b_mapping, ['CGST']) if not cdnr_t2b_df.empty else 0,
            get_mapped_sum(cdnr_t2b_df, cdnr_t2b_mapping, ['SGST']) if not cdnr_t2b_df.empty else 0,
            cn_t_total,
        ],
        [
            "Matched (CDNR)",
            f"=COUNTA('CDNR_Matched'!A2:A{max(2, tc(cdnr_matched) + 1)})" if not cdnr_matched.empty else 0,
            f"={_get_total_cell('CDNR_Matched', cdnr_matched, 'Taxable Amt.')}",
            f"={_get_total_cell('CDNR_Matched', cdnr_matched, 'IGST')}",
            f"={_get_total_cell('CDNR_Matched', cdnr_matched, 'CGST')}",
            f"={_get_total_cell('CDNR_Matched', cdnr_matched, 'SGST')}",
            f"={_get_total_cell('CDNR_Matched', cdnr_matched, 'Total Tax')}",
        ],
        [
            "Books Not in 2B (CDNR)",
            f"=COUNTA('CDNR_Books_Not_in_2B'!A2:A{max(2, tc(cdnr_un_books) + 1)})" if not cdnr_un_books.empty else 0,
            f"={_get_total_cell('CDNR_Books_Not_in_2B', cdnr_un_books, 'Taxable Value')}",
            f"={_get_total_cell('CDNR_Books_Not_in_2B', cdnr_un_books, 'IGST')}",
            f"={_get_total_cell('CDNR_Books_Not_in_2B', cdnr_un_books, 'CGST')}",
            f"={_get_total_cell('CDNR_Books_Not_in_2B', cdnr_un_books, 'SGST')}",
            "=D28+E28+F28",
        ],
        [
            "2B Not in Books (CDNR)",
            f"=COUNTA('CDNR_2B_Not_in_Books'!A2:A{max(2, tc(cdnr_un_2b) + 1)})" if not cdnr_un_2b.empty else 0,
            f"={_get_total_cell('CDNR_2B_Not_in_Books', cdnr_un_2b, 'Taxable Value')}",
            f"={_get_total_cell('CDNR_2B_Not_in_Books', cdnr_un_2b, 'IGST')}",
            f"={_get_total_cell('CDNR_2B_Not_in_Books', cdnr_un_2b, 'CGST')}",
            f"={_get_total_cell('CDNR_2B_Not_in_Books', cdnr_un_2b, 'SGST')}",
            "=D29+E29+F29",
        ],
    ]

    df_summary = pd.DataFrame(summary_rows)

    # ---- Write sheets ----
    _write_df_to_sheet(workbook, "Summary", df_summary, formats)
    _write_df_to_sheet(workbook, "B2B_Matched", b2b_matched, formats)
    _write_df_to_sheet(workbook, "B2B_Books_Not_in_2B", b2b_un_books, formats)
    _write_df_to_sheet(workbook, "B2B_2B_Not_in_Books", b2b_un_2b, formats)
    _write_df_to_sheet(workbook, "CDNR_Matched", cdnr_matched, formats)
    _write_df_to_sheet(workbook, "CDNR_Books_Not_in_2B", cdnr_un_books, formats)
    _write_df_to_sheet(workbook, "CDNR_2B_Not_in_Books", cdnr_un_2b, formats)

    workbook.close()
    return output.getvalue()


# ---------------------------------------------------------------------------
# Combined HTML report (B2B + CDNR)
# ---------------------------------------------------------------------------

def generate_html_report_combined(
    b2b_matched, b2b_un_books, b2b_un_2b, b2b_metrics,
    cdnr_matched, cdnr_un_books, cdnr_un_2b, cdnr_metrics,
    combined_metrics,
):
    """Return a self-contained HTML report with B2B and CDNR sections."""

    def _fmt(v):
        try:
            return f"{float(v):,.2f}"
        except (ValueError, TypeError):
            return str(v) if v is not None else "—"

    def _df_to_html_rows(df):
        if df.empty:
            return "<tr><td colspan='100%' style='text-align:center;padding:12px;color:#888;'>No records</td></tr>"
        rows = []
        for _, row in df.iterrows():
            cells = "".join(f"<td>{_fmt(v) if isinstance(v, (int, float)) else (v if pd.notna(v) else '—')}</td>" for v in row)
            rows.append(f"<tr>{cells}</tr>")
        return "\n".join(rows)

    def _df_to_table(df, title):
        if df.empty:
            headers = ""
        else:
            headers = "".join(f"<th>{c}</th>" for c in df.columns)
        return f"""
        <h3 style="margin-top:20px;">{title}</h3>
        <div style="overflow-x:auto;">
        <table>
          <thead><tr>{headers}</tr></thead>
          <tbody>{_df_to_html_rows(df)}</tbody>
        </table>
        </div>"""

    def _matched_table(df, title="Matched Records"):
        if df.empty:
            return _df_to_table(df, title)
        headers = "".join(f"<th>{c}</th>" for c in df.columns)
        rows = []
        for _, row in df.iterrows():
            cat = row.get("Category", "")
            if cat == "Exact Match":
                bg = "#d4edda"
            elif cat in ("Probable Match", "Most Likely Match"):
                bg = "#fff3cd"
            else:
                bg = "#f8d7da"
            cells = "".join(
                f"<td>{_fmt(v) if isinstance(v, (int, float)) else (v if pd.notna(v) else '—')}</td>"
                for v in row
            )
            rows.append(f"<tr style='background:{bg};'>{cells}</tr>")
        return f"""
        <h3 style="margin-top:20px;">{title}</h3>
        <div style="overflow-x:auto;">
        <table>
          <thead><tr>{headers}</tr></thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
        </div>"""

    def _metric_cards(m, prefix=""):
        return f"""
    <div class="metrics">
      <div class="metric-card"><div class="label">{prefix}Books Total ITC</div><div class="value">{_fmt(m.get('books_total_itc', 0))}</div></div>
      <div class="metric-card"><div class="label">{prefix}2B Total ITC</div><div class="value">{_fmt(m.get('t2b_total_itc', 0))}</div></div>
      <div class="metric-card"><div class="label">{prefix}Matched ITC</div><div class="value">{_fmt(m.get('matched_itc', 0))}</div></div>
      <div class="metric-card"><div class="label">{prefix}Books Risk</div><div class="value">{_fmt(m.get('books_risk_itc', 0))}</div></div>
      <div class="metric-card"><div class="label">{prefix}2B Risk</div><div class="value">{_fmt(m.get('t2b_risk_itc', 0))}</div></div>
      <div class="metric-card"><div class="label">{prefix}Matched</div><div class="value">{m.get('matched_count', 0)}</div></div>
      <div class="metric-card"><div class="label">{prefix}Books Count</div><div class="value">{m.get('books_invoice_count', 0)}</div></div>
      <div class="metric-card"><div class="label">{prefix}2B Count</div><div class="value">{m.get('t2b_invoice_count', 0)}</div></div>
      <div class="metric-card"><div class="label">{prefix}Books Not in 2B</div><div class="value">{m.get('un_books_count', 0)}</div></div>
      <div class="metric-card"><div class="label">{prefix}2B Not in Books</div><div class="value">{m.get('un_2b_count', 0)}</div></div>
    </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GSTR-2B Reconciliation Report</title>
<style>
  body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background: #f9f9f9; color: #333; }}
  h1 {{ color: #1a237e; border-bottom: 2px solid #1a237e; padding-bottom: 8px; }}
  h2 {{ color: #283593; margin-top: 40px; border-bottom: 1px solid #9fa8da; padding-bottom: 6px; }}
  .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 16px 0; }}
  .metric-card {{ background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 14px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .metric-card .label {{ font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }}
  .metric-card .value {{ font-size: 20px; font-weight: 700; margin-top: 4px; color: #1a237e; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; background: #fff; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; white-space: nowrap; }}
  th {{ background: #e0e0e0; font-weight: 600; position: sticky; top: 0; }}
  tr:nth-child(even) {{ background: #fafafa; }}
</style></head><body>
<h1>GSTR-2B Reconciliation Report</h1>

<h2>Combined Summary</h2>
{_metric_cards(combined_metrics)}

<h2>B2B — Invoice Reconciliation</h2>
{_metric_cards(b2b_metrics, "B2B ")}
{_matched_table(b2b_matched, "B2B Matched Records")}
{_df_to_table(b2b_un_books, "B2B — Books Not in 2B")}
{_df_to_table(b2b_un_2b, "B2B — 2B Not in Books")}

<h2>CDNR — Credit/Debit Note Reconciliation</h2>
{_metric_cards(cdnr_metrics, "CDNR ")}
{_matched_table(cdnr_matched, "CDNR Matched Records")}
{_df_to_table(cdnr_un_books, "CDNR — Books Not in 2B")}
{_df_to_table(cdnr_un_2b, "CDNR — 2B Not in Books")}

</body></html>"""
    return html
