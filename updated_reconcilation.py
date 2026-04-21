import streamlit as st
import pandas as pd
import numpy as np
import re
from rapidfuzz import fuzz
import io
import xlsxwriter

st.set_page_config(page_title="GST ITC Reconciliation", layout="wide")

# Custom CSS for Steps & Tiles
st.markdown("""
<style>
.step-container { display: flex; justify-content: space-between; margin-bottom: 2rem; }
.step { padding: 10px; border-radius: 5px; background: #262730; width: 23%; text-align: center; font-weight: bold; border: 1px solid #444; color: #fff; }
.step.active { background: #4CAF50; border-color: #4CAF50; color: white; }
.metric-container { background: #1E1E1E; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #333; margin-bottom: 1rem; }
.metric-label { font-size: 1.1rem; color: #aaa; margin-bottom: 5px; }
.metric-value { font-size: 1.8rem; font-weight: bold; color: #fff; }
.metric-sub { font-size: 1rem; color: #888; }
</style>
""", unsafe_allow_html=True)

if 'step' not in st.session_state:
    st.session_state.step = 1

def change_step(new_step):
    st.session_state.step = new_step

def render_steps(current_step):
    steps = ["1. Upload Data", "2. Map Headers", "3. Reconcile", "4. Dashboard"]
    html = '<div class="step-container">'
    for i, step in enumerate(steps, 1):
        active = "active" if i == current_step else ""
        html += f'<div class="step {active}">{step}</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def clean_inv(inv):
    if pd.isna(inv) or inv == '': return ""
    return re.sub(r'[^A-Z0-9]', '', str(inv).upper())

def process_reconciliation(df_books, df_2b, b_map, t_map):
    for col in list(df_books.columns):
        if col in b_map.values() and col not in b_map.keys():
            df_books = df_books.rename(columns={col: f"{col}_original"})
            
    for col in list(df_2b.columns):
        if col in t_map.values() and col not in t_map.keys():
            df_2b = df_2b.rename(columns={col: f"{col}_original"})

    # Normalize Headers
    df_books = df_books.rename(columns=b_map)
    df_2b = df_2b.rename(columns=t_map)
    
    def deduplicate(df):
        s = pd.Series(df.columns)
        dups = s[s.duplicated()].unique()
        for dup in dups:
            idx = s[s == dup].index
            for i, loc in enumerate(idx):
                if i != 0: s[loc] = f"{dup}_{i}"
        df.columns = s
        
    deduplicate(df_books)
    deduplicate(df_2b)
    
    # Ensure required columns exist to avoid KeyErrors if not mapped
    for col in ["GSTIN", "Party Name", "Invoice No"]:
        if col not in df_books.columns: df_books[col] = ""
        if col not in df_2b.columns: df_2b[col] = ""
    
    if "Invoice Date" not in df_books.columns: df_books["Invoice Date"] = np.nan
    if "Invoice Date" not in df_2b.columns: df_2b["Invoice Date"] = np.nan
    
    # Clean Data
    df_books['GSTIN'] = df_books['GSTIN'].astype(str).str.strip().str.upper().replace('NAN', '')
    df_2b['GSTIN'] = df_2b['GSTIN'].astype(str).str.strip().str.upper().replace('NAN', '')
    
    df_books['Clean_Inv'] = df_books['Invoice No'].apply(clean_inv)
    df_2b['Clean_Inv'] = df_2b['Invoice No'].apply(clean_inv)
    
    # Dates
    df_books['Invoice Date'] = pd.to_datetime(df_books['Invoice Date'], errors='coerce')
    df_2b['Invoice Date'] = pd.to_datetime(df_2b['Invoice Date'], errors='coerce')
    
    # Financials
    for c in ['Taxable Value', 'CGST', 'SGST', 'IGST']:
        if c not in df_books.columns: df_books[c] = 0
        if c not in df_2b.columns: df_2b[c] = 0
        df_books[c] = pd.to_numeric(df_books[c], errors='coerce').fillna(0)
        df_2b[c] = pd.to_numeric(df_2b[c], errors='coerce').fillna(0)
    
    df_books['TotalTax'] = df_books['CGST'] + df_books['SGST'] + df_books['IGST']
    df_2b['TotalTax'] = df_2b['CGST'] + df_2b['SGST'] + df_2b['IGST']
    
    matched_records = []
    books_unmatched = []
    t2b_unmatched = []
    
    # Make copies with unique indices
    df_books_enum = df_books.copy().reset_index()
    df_2b_enum = df_2b.copy().reset_index()
    
    all_gstins = set(df_books_enum['GSTIN'].unique()).union(set(df_2b_enum['GSTIN'].unique()))
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, gstin in enumerate(list(all_gstins)):
        if i % 10 == 0:
            progress_bar.progress(i / len(all_gstins))
        
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
            
        # Scoring logic
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
                    days = abs((b_date - t_date).days)
                    if days <= 5: date_score = 1
                
                if has_inv:
                    score = (inv_sim / 100 * 40) + (taxable_sim * 30) + (tax_sim * 20) + (date_score * 10)
                else:
                    score = (taxable_sim * 30) + (tax_sim * 20) + (date_score * 10)
                
                possible_matches.append((score, b_row, t_row, has_inv))
        
        possible_matches.sort(key=lambda x: x[0], reverse=True)
        b_used = set()
        t_used = set()
        
        for score, b_row, t_row, has_inv in possible_matches:
            if b_row['index'] in b_used or t_row['index'] in t_used: continue
            
            # Classification
            if has_inv:
                if score >= 90: cat = "Exact Match"
                elif score >= 70: cat = "Probable Match"
                else: cat = "Exception"
            else:
                if score >= 55: cat = "Most Likely Match"
                elif score >= 40: cat = "Probable Match"
                else: cat = "Exception"
            
            # Record match
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
            if b_row['index'] not in b_used: books_unmatched.append(b_row)
        for _, t_row in t_subset.iterrows():
            if t_row['index'] not in t_used: t2b_unmatched.append(t_row)
            
    progress_bar.progress(1.0)
    status_text.text("Reconciliation Complete!")
    
    df_matched = pd.DataFrame(matched_records)
    # Ensure columns exist even if empty
    if df_matched.empty:
        df_matched = pd.DataFrame(columns=['GSTIN', 'Party Name', 'Books Invoice No.', '2B Invoice No.', 'Match Score', 'Taxable Amt.', 'CGST', 'SGST', 'IGST', 'Total Tax', '2B Taxable Amt.', '2B CGST', '2B SGST', '2B IGST', '2B Total Tax', 'Tax Diff', 'Category'])
        
    df_books_un = pd.DataFrame(books_unmatched)
    if 'index' in df_books_un.columns: df_books_un = df_books_un.drop(columns=['index', 'Clean_Inv', 'TotalTax'])
    df_2b_un = pd.DataFrame(t2b_unmatched)
    if 'index' in df_2b_un.columns: df_2b_un = df_2b_un.drop(columns=['index', 'Clean_Inv', 'TotalTax'])
    
    return df_matched, df_books_un, df_2b_un

def read_2b_file(file):
    try:
        file.seek(0)
        xls = pd.ExcelFile(file)
        target_sheet = None
        for sheet in xls.sheet_names:
            if str(sheet).strip().upper() == "B2B":
                target_sheet = sheet
                break
        
        if target_sheet:
            df_raw = pd.read_excel(xls, sheet_name=target_sheet, header=None)
        else:
            file.seek(0)
            df_raw = pd.read_excel(file, header=None)
    except Exception:
        file.seek(0)
        df_raw = pd.read_excel(file, header=None)

    header_idx = 0
    is_multi_row = False
    
    for idx in range(min(15, len(df_raw))):
        try:
            row_values = df_raw.iloc[idx].dropna().astype(str).str.lower()
            row_str = " ".join(row_values)
            if 'gstin' in row_str and ('invoice' in row_str or 'inv' in row_str or 'name' in row_str or 'party' in row_str or 'date' in row_str):
                header_idx = idx
                break
        except Exception:
            break

    if header_idx + 1 < len(df_raw):
        row2_str = " ".join(df_raw.iloc[header_idx + 1].dropna().astype(str).str.lower())
        if 'taxable' in row2_str or 'integrated' in row2_str or 'central' in row2_str or 'sgst' in row2_str or 'igst' in row2_str or 'cgst' in row2_str or 'rate' in row2_str:
            is_multi_row = True

    if is_multi_row:
        row1 = df_raw.iloc[header_idx].ffill().fillna('')
        row2 = df_raw.iloc[header_idx + 1].fillna('')
        cols = []
        for c1, c2 in zip(row1, row2):
            c1, c2 = str(c1).strip(), str(c2).strip()
            if c1 and c2 and c1 != c2: cols.append(f"{c1} - {c2}")
            elif c1: cols.append(c1)
            elif c2: cols.append(c2)
            else: cols.append("Unnamed")
        
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

# Initialize Session Data
if 'books_df' not in st.session_state: st.session_state.books_df = None
if '2b_df' not in st.session_state: st.session_state['2b_df'] = None
if 'matched' not in st.session_state: st.session_state.matched = None
if 'un_books' not in st.session_state: st.session_state.un_books = None
if 'un_2b' not in st.session_state: st.session_state.un_2b = None

render_steps(st.session_state.step)

if st.session_state.step == 1:
    st.header("Step 1: Upload Files")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Books Purchase Data")
        books_file = st.file_uploader("Upload Books (Excel)", type=['xlsx', 'xls'], key="books")
    with col2:
        st.subheader("GSTR-2B Data")
        t2b_file = st.file_uploader("Upload 2B (Excel)", type=['xlsx', 'xls'], key="2b")
        
    if st.button("Next step: Map Headers", type="primary"):
        if books_file and t2b_file:
            with st.spinner("Reading Books file..."):
                books_file.seek(0)
                books_df = pd.read_excel(books_file)
                books_df.columns = [str(c).strip() for c in books_df.columns]
                st.session_state.books_df = books_df
            with st.spinner("Reading GSTR-2B file..."):
                try:
                    t2b_file.seek(0)
                    df_2b = read_2b_file(t2b_file)
                except Exception as e:
                    st.warning("Could not auto-detect 'B2B' sheet and headers automatically. Loading default.")
                    t2b_file.seek(0)
                    df_2b = pd.read_excel(t2b_file)
                    df_2b.columns = [str(c).strip() for c in df_2b.columns]
                st.session_state['2b_df'] = df_2b
            change_step(2)
            st.rerun()
        else:
            st.error("Please upload both files first.")

elif st.session_state.step == 2:
    st.header("Step 2: Map Headers")
    req_cols = ["GSTIN", "Party Name", "Invoice No", "Invoice Date", "Taxable Value", "CGST", "SGST", "IGST"]
    
    st.write("Ensure your uploaded columns match the required fields.")
    
    col1, col2 = st.columns(2)
    books_mapping = {}
    t2b_mapping = {}
    
    with col1:
        st.subheader("Books Headers")
        b_cols = [""] + list(st.session_state.books_df.columns)
        for req in req_cols:
            best_match = ""
            for x in b_cols:
                if req.lower() in x.lower() or x.lower() in req.lower():
                    if x != "":
                        best_match = x
                        break
            idx = b_cols.index(best_match) if best_match else 0
            sel = st.selectbox(f"Select column for '{req}' (Books)", options=b_cols, index=idx, key=f"b_{req}")
            if sel: books_mapping[sel] = req
            
    with col2:
        st.subheader("2B Headers")
        t_cols = [""] + list(st.session_state['2b_df'].columns)
        for req in req_cols:
            best_match = ""
            for x in t_cols:
                if req.lower() in x.lower() or x.lower() in req.lower():
                    if x != "":
                        best_match = x
                        break
            idx = t_cols.index(best_match) if best_match else 0
            sel = st.selectbox(f"Select column for '{req}' (2B)", options=t_cols, index=idx, key=f"t_{req}")
            if sel: t2b_mapping[sel] = req

    colA, colB = st.columns([1, 8])
    with colA:
        if st.button("Back"):
            change_step(1)
            st.rerun()
    with colB:
        if st.button("Run Reconciliation", type="primary"):
            st.session_state.books_mapping = books_mapping
            st.session_state.t2b_mapping = t2b_mapping
            change_step(3)
            st.rerun()

elif st.session_state.step == 3:
    st.header("Step 3: Reconciling Data")
    with st.spinner("Processing reconciliation matching..."):
        matched, un_books, un_2b = process_reconciliation(
            st.session_state.books_df, 
            st.session_state['2b_df'],
            st.session_state.books_mapping,
            st.session_state.t2b_mapping
        )
        st.session_state.matched = matched
        st.session_state.un_books = un_books
        st.session_state.un_2b = un_2b
        change_step(4)
        st.rerun()

elif st.session_state.step == 4:
    st.header("Step 4: Output Dashboard")
    
    # Calculate Metrics
    matched = st.session_state.matched
    un_books = st.session_state.un_books
    un_2b = st.session_state.un_2b
    
    # Safely calculate basic metrics
    def safe_sum(df, col): return df[col].sum() if not df.empty and col in df else 0
    def tc(df): return len(df)
    
    # Extract total ITC safely based on mappings
    b_itc_col = [cmd for cmd, v in st.session_state.books_mapping.items() if v in ['CGST','SGST','IGST']]
    b_total_itc = st.session_state.books_df[b_itc_col].apply(pd.to_numeric, errors='coerce').sum().sum()
    t_itc_col = [cmd for cmd, v in st.session_state.t2b_mapping.items() if v in ['CGST','SGST','IGST']]
    t_total_itc = st.session_state['2b_df'][t_itc_col].apply(pd.to_numeric, errors='coerce').sum().sum()
    
    matched_itc = safe_sum(matched, 'Total Tax')
    books_risk_itc = sum(safe_sum(un_books, v) for v in ['CGST','SGST','IGST']) if not un_books.empty else 0
    t2b_risk_itc = sum(safe_sum(un_2b, v) for v in ['CGST','SGST','IGST']) if not un_2b.empty else 0
    
    def fmt(val): return f"₹ {val:,.2f}"
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="metric-container"><div class="metric-label">Books / GSTR 2B Total</div>'
                    f'<div class="metric-value">{fmt(b_total_itc)}<br>{fmt(t_total_itc)}</div>'
                    f'<div class="metric-sub">{tc(st.session_state.books_df)} / {tc(st.session_state["2b_df"])} Invoices</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-container"><div class="metric-label">Matched</div>'
                    f'<div class="metric-value">{fmt(matched_itc)}</div>'
                    f'<div class="metric-sub">{tc(matched)} Invoices matched</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-container"><div class="metric-label">Not in 2B</div>'
                    f'<div class="metric-value">{fmt(books_risk_itc)}</div>'
                    f'<div class="metric-sub">{tc(un_books)} Invoices at risk</div></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-container"><div class="metric-label">Not in Books</div>'
                    f'<div class="metric-value">{fmt(t2b_risk_itc)}</div>'
                    f'<div class="metric-sub">{tc(un_2b)} Invoices at risk</div></div>', unsafe_allow_html=True)
    
    view_select = st.radio("Select View to Preview Data:", ["Matched", "Not in 2B", "Not in Books"], horizontal=True)
    
    st.markdown("---")
    if view_select == "Matched":
        st.dataframe(matched, use_container_width=True, height=300)
    elif view_select == "Not in 2B":
        st.dataframe(un_books, use_container_width=True, height=300)
    else:
        st.dataframe(un_2b, use_container_width=True, height=300)
        
    st.markdown("---")
    
    # Export logic
    def to_excel():
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        format_num = workbook.add_format({'num_format': '#,##,##0.00'})
        format_date = workbook.add_format({'num_format': 'dd-mm-yyyy'})
        format_head = workbook.add_format({'bold': True, 'bg_color': '#E0E0E0', 'border': 1})
        format_text = workbook.add_format({})
        format_total_text = workbook.add_format({'bold': True, 'bg_color': '#FFFFCC', 'border': 1})
        format_total_num = workbook.add_format({'num_format': '#,##,##0.00', 'bold': True, 'bg_color': '#FFFFCC', 'border': 1})
        
        def get_col_letter(col_idx):
            res = ""
            while col_idx >= 0:
                res = chr((col_idx % 26) + 65) + res
                col_idx = (col_idx // 26) - 1
            return res

        def get_total_cell(sheet_name, df, col_name):
            if df.empty or col_name not in df.columns:
                return "0"
            col_idx = df.columns.get_loc(col_name)
            if isinstance(col_idx, np.ndarray): col_idx = col_idx[0]
            letter = get_col_letter(col_idx)
            return f"'{sheet_name}'!{letter}{len(df)+2}"

        def write_df_to_sheet(sheet_name, df):
            sheet = workbook.add_worksheet(sheet_name)
            if df.empty: return
            
            is_data_sheet = sheet_name in ["Matched", "Books_Not_in_2B", "2B_Not_in_Books"]
            if is_data_sheet:
                df = df.copy()
                total_row = {col: "" for col in df.columns}
                if len(df.columns) > 0:
                    total_row[df.columns[0]] = "Grand Total"
                for col_idx, col in enumerate(df.columns):
                    col_str = str(col).upper()
                    if any(kw in col_str for kw in ['TAXABLE', 'CGST', 'SGST', 'IGST', 'TAX', 'CESS']):
                        if 'INV' not in col_str and 'RATE' not in col_str:
                            letter = get_col_letter(col_idx)
                            total_row[col] = f"=SUM({letter}2:{letter}{len(df)+1})"
                df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
                
            df = df.fillna("")
            
            for col_num, value in enumerate(df.columns.values):
                sheet.write(0, col_num, value, format_head)
                
            for row_num, row_data in enumerate(df.values):
                is_total_row = is_data_sheet and row_num == len(df) - 1
                for col_num, val in enumerate(row_data):
                    col_name = df.columns[col_num]
                    # formatting logic
                    if str(val).startswith('='):
                        sheet.write_formula(row_num + 1, col_num, str(val), format_total_num if is_total_row else format_num)
                    elif "date" in str(col_name).lower() and val != "" and not is_total_row:
                        try:
                            # if it's a pandas timestamp object
                            if pd.notna(val):
                                sheet.write_datetime(row_num + 1, col_num, pd.to_datetime(val), format_date)
                            else:
                                sheet.write(row_num + 1, col_num, val, format_text)
                        except: sheet.write(row_num + 1, col_num, str(val), format_text)
                    elif isinstance(val, (int, float)) and pd.notna(val):
                        sheet.write_number(row_num + 1, col_num, val, format_total_num if is_total_row else format_num)
                    else:
                        is_heading = (val == col_name) and (row_num > 0)
                        f = format_head if is_heading else format_total_text if is_total_row else format_text
                        sheet.write(row_num + 1, col_num, str(val), f)
                        
            # Autofit logic simple approximation
            for col_num, col_name in enumerate(df.columns.values):
                max_len = max(
                    [len(str(val)) for val in df.iloc[:, col_num].values] + [len(str(col_name))]
                ) + 2
                sheet.set_column(col_num, col_num, max_len)

        def get_mapped_sum(df, mapping, fields):
            cols = [cmd for cmd, v in mapping.items() if v in fields]
            if not cols: return 0
            if df.empty: return 0
            return df[cols].apply(pd.to_numeric, errors='coerce').sum().sum()

        # Create a Summary dataframe
        summary_data = {
            "Position / Category": [
                "Total Uploaded - Books Data",
                "Total Uploaded - GSTR 2B Data",
                "Matched (Available in both)",
                "Books records Not in 2B (Books Risk)",
                "2B records Not in Books (2B Risk)"
            ],
            "Invoice Count": [
                tc(st.session_state.books_df),
                tc(st.session_state['2b_df']),
                f"=COUNTA('Matched'!A2:A{max(2, len(matched)+1)})" if not matched.empty else 0,
                f"=COUNTA('Books_Not_in_2B'!A2:A{max(2, len(un_books)+1)})" if not un_books.empty else 0,
                f"=COUNTA('2B_Not_in_Books'!A2:A{max(2, len(un_2b)+1)})" if not un_2b.empty else 0
            ],
            "Taxable Value": [
                get_mapped_sum(st.session_state.books_df, st.session_state.books_mapping, ['Taxable Value']),
                get_mapped_sum(st.session_state['2b_df'], st.session_state.t2b_mapping, ['Taxable Value']),
                f"={get_total_cell('Matched', matched, 'Taxable Amt.')}",
                f"={get_total_cell('Books_Not_in_2B', un_books, 'Taxable Value')}",
                f"={get_total_cell('2B_Not_in_Books', un_2b, 'Taxable Value')}"
            ],
            "IGST": [
                get_mapped_sum(st.session_state.books_df, st.session_state.books_mapping, ['IGST']),
                get_mapped_sum(st.session_state['2b_df'], st.session_state.t2b_mapping, ['IGST']),
                f"={get_total_cell('Matched', matched, 'IGST')}",
                f"={get_total_cell('Books_Not_in_2B', un_books, 'IGST')}",
                f"={get_total_cell('2B_Not_in_Books', un_2b, 'IGST')}"
            ],
            "CGST": [
                get_mapped_sum(st.session_state.books_df, st.session_state.books_mapping, ['CGST']),
                get_mapped_sum(st.session_state['2b_df'], st.session_state.t2b_mapping, ['CGST']),
                f"={get_total_cell('Matched', matched, 'CGST')}",
                f"={get_total_cell('Books_Not_in_2B', un_books, 'CGST')}",
                f"={get_total_cell('2B_Not_in_Books', un_2b, 'CGST')}"
            ],
            "SGST": [
                get_mapped_sum(st.session_state.books_df, st.session_state.books_mapping, ['SGST']),
                get_mapped_sum(st.session_state['2b_df'], st.session_state.t2b_mapping, ['SGST']),
                f"={get_total_cell('Matched', matched, 'SGST')}",
                f"={get_total_cell('Books_Not_in_2B', un_books, 'SGST')}",
                f"={get_total_cell('2B_Not_in_Books', un_2b, 'SGST')}"
            ],
            "Total Tax Amount": [
                b_total_itc,
                t_total_itc,
                f"={get_total_cell('Matched', matched, 'Total Tax')}",
                f"=D5+E5+F5",
                f"=D6+E6+F6"
            ]
        }
        df_summary = pd.DataFrame(summary_data)
        
        cross_check_data = {
            "Position / Category": [
                "",
                "Position / Category",
                "[CROSS CHECK] 1. Books Validation",
                "   -> Total from Uploaded Books",
                "   -> Matched (Books figures)",
                "   -> Books Not in 2B",
                "   -> Total Accounted For",
                "   -> Books Variance (Difference)",
                "",
                "[CROSS CHECK] 2. GSTR-2B Validation",
                "   -> Total from Uploaded GSTR 2B",
                "   -> Matched (2B figures)",
                "   -> 2B Not in Books",
                "   -> Total Accounted For",
                "   -> 2B Variance (Difference)"
            ],
            "Invoice Count": [
                "",
                "Invoice Count",
                "", "=B2", "=B4", "=B5", "=B11+B12", "=B10-B13",
                "",
                "", "=B3", "=B4", "=B6", "=B18+B19", "=B17-B20"
            ],
            "Taxable Value": [
                "",
                "Taxable Value",
                "", "=C2", "=C4", "=C5", "=C11+C12", "=C10-C13",
                "",
                "", "=C3", f"={get_total_cell('Matched', matched, '2B Taxable Amt.')}", "=C6", "=C18+C19", "=C17-C20"
            ],
            "IGST": [
                "",
                "IGST",
                "", "=D2", "=D4", "=D5", "=D11+D12", "=D10-D13",
                "",
                "", "=D3", f"={get_total_cell('Matched', matched, '2B IGST')}", "=D6", "=D18+D19", "=D17-D20"
            ],
            "CGST": [
                "",
                "CGST",
                "", "=E2", "=E4", "=E5", "=E11+E12", "=E10-E13",
                "",
                "", "=E3", f"={get_total_cell('Matched', matched, '2B CGST')}", "=E6", "=E18+E19", "=E17-E20"
            ],
            "SGST": [
                "",
                "SGST",
                "", "=F2", "=F4", "=F5", "=F11+F12", "=F10-F13",
                "",
                "", "=F3", f"={get_total_cell('Matched', matched, '2B SGST')}", "=F6", "=F18+F19", "=F17-F20"
            ],
            "Total Tax Amount": [
                "",
                "Total Tax Amount",
                "", "=G2", "=G4", "=G5", "=G11+G12", "=G10-G13",
                "",
                "", "=G3", f"={get_total_cell('Matched', matched, '2B Total Tax')}", "=G6", "=G18+G19", "=G17-G20"
            ]
        }
        df_cross_check = pd.DataFrame(cross_check_data)
        df_combined = pd.concat([df_summary, df_cross_check], ignore_index=True)
        
        write_df_to_sheet("Summary", df_combined)
        write_df_to_sheet("Matched", matched)
        write_df_to_sheet("Books_Not_in_2B", un_books)
        write_df_to_sheet("2B_Not_in_Books", un_2b)
        
        workbook.close()
        return output.getvalue()

    excel_data = to_excel()
    st.download_button(
        label="Download Reconciliation Excel Report",
        data=excel_data,
        file_name="Reconciliation_Output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )
    
    if st.button("Start New Reconciliation"):
        st.session_state.clear()
        st.rerun()
