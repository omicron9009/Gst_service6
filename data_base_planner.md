# Data Base Planner: Service Return Structures

Date: 2026-03-30
Scope: all files in services/ excluding __pycache__
Goal: document exact return structures from API-calling service functions (BASE_URL-based calls), including parser-shaped outputs and error variants.

## 1) Common API Envelope Patterns

Most services consume upstream responses in this envelope:

```python
{
  "data": {
    "status_cd": "1" | "0" | "3" | "P" | "PE" | "ER" | "REC",
    "error": {
      "error_cd": "...",
      "message": "..."
    },
    "data": { ...endpoint specific payload... }
  }
}
```

Common return keys used by service functions:
- success: bool
- status_cd: string (when propagated)
- message: string (for failures/notes)
- error_code: string (for status_cd == "0" patterns)
- request: object (echoed request metadata in many functions)
- upstream_status_code or status_code: int (HTTP response code)
- raw or upstream_response: full/partial upstream payload for traceability

---

## 2) services/auth.py

Base URL usage:
- f"{BASE_URL}/authenticate"
- f"{BASE_URL}/gst/compliance/tax-payer/otp"
- f"{BASE_URL}/gst/compliance/tax-payer/otp/verify?..."
- f"{BASE_URL}/gst/compliance/tax-payer/session/refresh"

### 2.1 generate_otp(username, gstin)
Endpoint: POST `{BASE_URL}/gst/compliance/tax-payer/otp`

Success return shape:
```python
{
  "request_sent": True,
  "success": True,
  "message": "OTP sent successfully",
  "error_code": None,
  "status_cd": <status_cd>,
  "upstream_status_code": <int>,
  "upstream_response": <dict>
}
```

Failure return shape:
```python
{
  "request_sent": False or True,
  "success": False,
  "message": <string>,
  "error": <string optional>
}
```

### 2.2 verify_otp(username, gstin, otp)
Endpoint: POST `{BASE_URL}/gst/compliance/tax-payer/otp/verify?otp=...`

Success return shape:
```python
{
  "request_sent": True,
  "success": True,
  "session_saved": True,
  "message": "Session established successfully",
  "error_code": None,
  "status_cd": <status_cd>,
  "upstream_status_code": <int>,
  "data": {
    "access_token": <string>,
    "refresh_token": <string>,
    "token_expiry": <string|None>,
    "session_expiry": <string|None>
  },
  "upstream_response": <dict>
}
```

Failure return shapes:
```python
{
  "request_sent": True,
  "success": False,
  "message": <string>,
  "error_code": <string|None>,
  "status_cd": <string|None>,
  "upstream_status_code": <int>,
  "upstream_response": <dict>
}
```
or transport/session errors:
```python
{
  "request_sent": False,
  "success": False,
  "message": <string>,
  "error": <string optional>
}
```

### 2.3 refresh_session(gstin)
Endpoint: POST `{BASE_URL}/gst/compliance/tax-payer/session/refresh`

Success return shape:
```python
{
  "request_sent": True,
  "success": True,
  "session_saved": True,
  "message": "Session refreshed successfully",
  "error_code": None,
  "status_cd": <status_cd>,
  "upstream_status_code": <int>,
  "data": {
    "access_token": <string>,
    "refresh_token": <string|None>,
    "token_expiry": <string|None>,
    "session_expiry": <string|None>
  },
  "upstream_response": <dict>
}
```

Failure return shape:
```python
{
  "request_sent": False or True,
  "success": False,
  "message": <string>
}
```

Persistence note:
- verify_otp and refresh_session persist session data through save_session(...).

---

## 3) services/gstr1_service.py

Base URL prefix:
- `{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-1/...`

### 3.1 get_gstr1_advance_tax(gstin, year, month)
Endpoint: GET `/at/{year}/{month}`
Parser: parsers/gstr1_parser.py -> parse_gstr1_advance_tax(payload)

Success return shape:
```python
{
  "success": True,
  "request": {"gstin": ..., "year": ..., "month": ...},
  "upstream_status_code": <int>,
  "data": {
    "raw": <payload["data"]["data"]["at"]>,
    "parsed": [
      {
        "place_of_supply": <string>,
        "supply_type": <string>,
        "items": [
          {
            "rate": <number>,
            "taxable_value": <number>,
            "igst": <number>,
            "cgst": <number>,
            "sgst": <number>,
            "cess": <number>
          }
        ]
      }
    ]
  }
}
```

Failure shape:
```python
{"success": False, "message": <string>, "error": <string optional>}
```

### 3.2 get_gstr1_b2b(...)
Endpoint: GET `/b2b/{year}/{month}`

Success return shape:
```python
{
  "success": True,
  "summary": {
    "total_invoices": <int>,
    "total_taxable_value": <number>,
    "total_cgst": <number>,
    "total_sgst": <number>,
    "total_igst": <number>
  },
  "invoices": [
    {
      "counterparty_gstin": <string>,
      "invoice_number": <string>,
      "invoice_date": <string>,
      "invoice_value": <number>,
      "items": [
        {
          "rate": <number>,
          "taxable_value": <number>,
          "igst": <number>,
          "cgst": <number>,
          "sgst": <number>,
          "cess": <number>
        }
      ]
    }
  ],
  "raw": <list>
}
```

Failure shape: `{"success": False, "message": <string>}`

### 3.3 get_gstr1_summary(gstin, year, month, summary_type)
Endpoint: GET `/{year}/{month}?summary_type=...`

Success return shape:
```python
{
  "success": True,
  "gstin": <string>,
  "ret_period": <string>,
  "summary_type": "short"|"long",
  "sections": [
    {
      "sec_nm": <string>,
      "ttl_rec": <number>,
      "ttl_val": <number>,
      "ttl_tax": <number>
    }
  ],
  "raw": <dict|list>
}
```

Failure shape: `{"success": False, "message": <string>}`

### 3.4 get_gstr1_b2csa(gstin, year, month)
Endpoint: GET `/b2csa/{year}/{month}`

Success return shape:
```python
{
  "success": True,
  "request": {...},
  "upstream_status_code": <int>,
  "records": [
    {
      "pos": <string>,
      "supply_type": <string>,
      "invoice_type": <string>,
      "rt": <number>,
      "txval": <number>,
      "iamt": <number>,
      "camt": <number>,
      "samt": <number>,
      "csamt": <number>
    }
  ],
  "raw": <list>
}
```

### 3.5 get_gstr1_b2cs(gstin, year, month)
Endpoint: GET `/b2cs/{year}/{month}`

Success return shape:
```python
{
  "success": True,
  "request": {
    "gstin": <string>,
    "year": <string>,
    "month": <string>,
    "endpoint": "GSTR-1 B2CS"
  },
  "upstream_status_code": <int>,
  "records": [
    {
      "place_of_supply": <string>,
      "supply_type": <string>,
      "invoice_type": <string>,
      "tax_rate": <number>,
      "taxable_value": <number>,
      "igst": <number>,
      "cgst": <number>,
      "sgst": <number>,
      "cess": <number>,
      "checksum": <string|None>,
      "flag": <string|None>
    }
  ],
  "raw": <dict>
}
```

### 3.6 get_gstr1_cdnr(gstin, year, month, action_required, from_date)
Endpoint: GET `/cdnr/{year}/{month}`

Success return shape:
```python
{
  "success": True,
  "request": {...},
  "upstream_status_code": <int>,
  "record_count": <int>,
  "records": [
    {
      "counterparty_gstin": <string>,
      "note_number": <string>,
      "note_date": <string>,
      "note_type": <string>,
      "items": [ ...tax lines... ]
    }
  ],
  "raw": <list>
}
```

### 3.7 get_gstr1_doc_issue(gstin, year, month)
Endpoint: GET `/doc-issue/{year}/{month}`

Success return shape:
```python
{
  "success": True,
  "request": {
    "gstin": <string>,
    "year": <string>,
    "month": <string>,
    "endpoint": "GSTR-1 Document Issued"
  },
  "upstream_status_code": <int>,
  "records": [
    {
      "document_type_number": <string|int|None>,
      "serial_number": <string|int|None>,
      "from_serial": <string|int|None>,
      "to_serial": <string|int|None>,
      "total_issued": <number>,
      "cancelled": <number>,
      "net_issued": <number>
    }
  ],
  "raw": <dict>
}
```

### 3.8 get_gstr1_hsn(gstin, year, month)
Endpoint: GET `/hsn/{year}/{month}`

Success return shape:
```python
{
  "success": True,
  "request": {
    "gstin": <string>,
    "year": <string>,
    "month": <string>,
    "endpoint": "GSTR-1 HSN Summary"
  },
  "upstream_status_code": <int>,
  "records": [
    {
      "serial_number": <string|int|None>,
      "hsn_sac_code": <string|None>,
      "description": <string|None>,
      "unit_of_quantity": <string|None>,
      "quantity": <number|None>,
      "tax_rate": <number|None>,
      "taxable_value": <number|None>,
      "igst": <number|None>,
      "cgst": <number|None>,
      "sgst": <number|None>
    }
  ],
  "raw": <dict>
}
```

### 3.9 get_gstr1_nil(gstin, year, month)
Endpoint: GET `/nil/{year}/{month}`

Success return shape:
```python
{
  "success": True,
  "request": {
    "gstin": <string>,
    "year": <string>,
    "month": <string>,
    "endpoint": "GSTR-1 Nil Rated"
  },
  "upstream_status_code": <int>,
  "records": [
    {
      "supply_type_code": <string|None>,
      "supply_type": <string|None>,
      "nil_rated_amount": <number|None>,
      "exempted_amount": <number|None>,
      "non_gst_amount": <number|None>
    }
  ],
  "raw": <dict>
}
```

### 3.10 get_gstr1_b2cl(gstin, year, month, state_code)
Endpoint: GET `/b2cl/{year}/{month}`

Success return shape:
- records[] with place_of_supply, invoice_number, invoice_date, invoice_value, flag
- nested items[] with rt, txval, iamt, cgst, sgst, cess

### 3.11 get_gstr1_cdnur(gstin, year, month)
Endpoint: GET `/cdnur/{year}/{month}`

Success return shape:
```python
{
  "success": True,
  "request": {...},
  "upstream_status_code": <int>,
  "records": <list>,
  "raw": <list>
}
```

### 3.12 get_gstr1_exp(gstin, year, month)
Endpoint: GET `/exp/{year}/{month}`

Success return shape:
```python
{
  "success": True,
  "request": {
    "gstin": <string>,
    "year": <string>,
    "month": <string>,
    "endpoint": "GSTR-1 EXP"
  },
  "upstream_status_code": <int>,
  "records": [
    {
      "export_type_code": <string|None>,
      "export_type": <string|None>,
      "invoice_number": <string|None>,
      "invoice_date": <string|None>,
      "invoice_value": <number|None>,
      "flag": <string|None>,
      "items": [
        {
          "tax_rate": <number|None>,
          "taxable_value": <number|None>,
          "igst": <number|None>,
          "cess": <number|None>
        }
      ]
    }
  ],
  "raw": <dict>
}
```

### 3.13 get_gstr1_txp(gstin, year, month, counterparty_gstin, action_required, from_date)
Endpoint: GET `/txp/{year}/{month}`

Success return shape:
- success/request/upstream_status_code
- records: list of tax payment/adjustment blocks from `payload["data"]["data"]["data"]["txp"]`
- raw: source list

Common failure shape across 3.4-3.13:
```python
{"success": False, "message": <string>, "error": <string optional>}
```

---

## 4) services/gstr_2A_service.py

Base URL prefix:
- `{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2a/...`

### 4.1 get_gstr2a_b2b(gstin, year, month)
Endpoint: GET `/b2b/{year}/{month}`

Success return shape:
```python
{
  "success": True,
  "request": {...},
  "upstream_status_code": <int>,
  "records": [
    {
      "supplier_gstin": <string>,
      "filing_status_gstr1": <string>,
      "invoice_number": <string>,
      "invoice_date": <string>,
      "items": [ ... ]
    }
  ],
  "raw": <list>
}
```

### 4.2 get_gstr2a_b2ba(gstin, year, month, counterparty_gstin)
Endpoint: GET `/b2ba/{year}/{month}`

Success return shape:
```python
{
  "success": True,
  "request": {
    "gstin": <string>,
    "year": <string>,
    "month": <string>,
    "counterparty_gstin": <string|None>,
    "endpoint": "GSTR-2A B2BA"
  },
  "upstream_status_code": <int>,
  "records": [
    {
      "supplier_gstin": <string|None>,
      "filing_status_gstr1": <string|None>,
      "filing_status_gstr3b": <string|None>,
      "supplier_filed_date": <string|None>,
      "supplier_filing_period": <string|None>,
      "invoice_number": <string|None>,
      "invoice_date": <string|None>,
      "original_invoice_number": <string|None>,
      "original_invoice_date": <string|None>,
      "amendment_period": <string|None>,
      "amendment_type_code": <string|None>,
      "amendment_type": <string|None>,
      "invoice_type": <string|None>,
      "invoice_value": <number|None>,
      "place_of_supply": <string|None>,
      "reverse_charge": <string|None>,
      "items": [
        {
          "item_number": <int|None>,
          "tax_rate": <number|None>,
          "taxable_value": <number|None>,
          "igst": <number|None>,
          "cgst": <number|None>,
          "sgst": <number|None>,
          "cess": <number|None>
        }
      ]
    }
  ],
  "raw": <dict>
}
```

### 4.3 get_gstr2a_cdn(gstin, year, month, counterparty_gstin, from_date)
Endpoint: GET `/cdn/{year}/{month}`

Success return shape:
```python
{
  "success": True,
  "request": {
    "gstin": <string>,
    "year": <string>,
    "month": <string>,
    "counterparty_gstin": <string|None>,
    "from_date": <string|None>,
    "endpoint": "GSTR-2A CDN"
  },
  "upstream_status_code": <int>,
  "records": [
    {
      "supplier_gstin": <string|None>,
      "filing_status_gstr1": <string|None>,
      "filing_status_gstr3b": <string|None>,
      "supplier_filed_date": <string|None>,
      "supplier_filing_period": <string|None>,
      "note_number": <string|None>,
      "note_date": <string|None>,
      "note_type_code": <string|None>,
      "note_type": <string|None>,
      "invoice_type": <string|None>,
      "note_value": <number|None>,
      "place_of_supply": <string|None>,
      "reverse_charge": <string|None>,
      "delete_flag": <string|None>,
      "source_type": <string|None>,
      "irn": <string|None>,
      "irn_gen_date": <string|None>,
      "items": [
        {
          "item_number": <int|None>,
          "tax_rate": <number|None>,
          "taxable_value": <number|None>,
          "igst": <number|None>,
          "cgst": <number|None>,
          "sgst": <number|None>,
          "cess": <number|None>
        }
      ]
    }
  ],
  "raw": <dict>
}
```

### 4.4 get_gstr2a_cdna(gstin, year, month, counterparty_gstin)
Endpoint: GET `/cdna/{year}/{month}`

Success return shape:
- success/request/upstream_status_code/records/raw

### 4.5 get_gstr2a_document(gstin, year, month)
Endpoint: GET `/documents/{year}/{month}`
Inline parser helpers: parse_items, parse_b2b, parse_b2ba, parse_cdn

Success return shape:
```python
{
  "success": True,
  "request": {...},
  "upstream_status_code": <int>,
  "b2b": [...parsed...],
  "b2ba": [...parsed...],
  "cdn": [...parsed...],
  "summary": {
    "all": {...},
    "pending_action": {...}
  },
  "raw": <dict>
}
```

### 4.6 get_gstr2a_isd(gstin, year, month, counterparty_gstin)
Endpoint: GET `/isd/{year}/{month}`

Success return shape records include:
- isd_gstin, document_number, document_date, document_type, itc_available, igst, cgst, sgst, cess

### 4.7 get_gstr2a_tds(gstin, year, month)
Endpoint: GET `/tds/{year}/{month}`
Helper parser: `_parse_tds_entry(entry)`

Success return shape:
```python
{
  "success": True,
  "tds": [ ...normalized entries... ],
  "entry_count": <int>,
  "grand_totals": {
    "deduction_base_amount": <number>,
    "igst": <number>,
    "cgst": <number>,
    "sgst": <number>,
    "total_tds_credit": <number>
  },
  "raw": <list>
}
```

Common failure shape in this file:
```python
{"success": False, "message": <string>, "error": <string optional>}
```

---

## 5) services/gstr_2B_service.py

Base URL usage:
- `{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2b/{year}/{month}`
- `{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-2b/regeneration-status`

Internal section parsers:
- _parse_b2b_section
- _parse_cdnr_section
- _parse_isd_section
- _parse_cpsumm
- _parse_itcsumm

### 5.1 get_gstr2b(gstin, year, month, file_number=None)
Endpoint: GET `/gstr-2b/{year}/{month}` (+ optional file_number)

This function has multiple return variants.

Variant A: upstream status_cd == "0"
```python
{
  "success": False,
  "status_cd": "0",
  "error_code": <string|None>,
  "message": <string>,
  "raw": <dict>
}
```

Variant B: upstream status_cd == "3" (pagination required)
```python
{
  "success": True,
  "status_cd": "3",
  "pagination_required": True,
  "file_count": <int>,
  "gstin": <string>,
  "return_period": <string>,
  "gen_date": <string>,
  "message": <string>,
  "raw": <dict>
}
```

Variant C: summary shape
```python
{
  "success": True,
  "status_cd": "1",
  "response_type": "summary",
  "gstin": <string>,
  "return_period": <string>,
  "gen_date": <string>,
  "version": <string|None>,
  "checksum": <string|None>,
  "file_count": <int|None>,
  "counterparty_summary": {
    "b2b": <parsed>,
    "cdnr": <parsed>
  },
  "itc_summary": <parsed>,
  "raw": <dict>
}
```

Variant D: documents shape
```python
{
  "success": True,
  "status_cd": "1",
  "response_type": "documents",
  "gstin": <string>,
  "return_period": <string>,
  "gen_date": <string>,
  "version": <string|None>,
  "checksum": <string|None>,
  "file_count": <int|None>,
  "file_number": <int|None>,
  "b2b": {"invoices": [...], "summary": {...}},
  "b2ba": {"invoices": [...], "summary": {...}},
  "cdnr": {"notes": [...], "summary": {...}},
  "cdnra": {"notes": [...], "summary": {...}},
  "isd": {"entries": [...], "summary": {...}},
  "grand_summary": {...},
  "itc_summary": <parsed>,
  "raw": <dict>
}
```

### 5.2 get_gstr2b_regeneration_status(gstin, reference_id)
Endpoint: GET `/gstr-2b/regeneration-status`

Success return shape:
```python
{
  "success": True,
  "status_cd": <string>,
  "form_type_label": <string>,
  "action": <string>,
  "processing_status_label": <string>,
  "has_errors": <bool>,
  "error_report": {
    ...nested section errors...
  },
  "raw": <dict>
}
```

Failure shape:
```python
{"success": False, "message": <string>, "error": <string optional>}
```

---

## 6) services/gstr_3B_service.py

Base URL prefix:
- `{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-3b/...`

### 6.1 get_gstr3b_details(gstin, year, month)
Endpoint: GET `/gstr-3b/{year}/{month}`

Success return shape:
```python
{
  "success": True,
  "status_cd": <string>,
  "gstin": <string>,
  "return_period": <string>,
  "supply_details": {
    "outward_taxable_supplies": {...},
    "outward_zero_rated": {...},
    "outward_nil_exempt_non_gst": {...},
    ...
  },
  "inter_state_supplies": {
    "unregistered_persons": {...},
    "composition_dealers": {...},
    "uin_holders": {...}
  },
  "eligible_itc": {
    "itc_available": [...],
    "itc_reversed": [...],
    "itc_ineligible": [...],
    "itc_net": {...}
  },
  "inward_supplies": {...},
  "interest_and_late_fee": {...},
  "tax_payment": {
    "net_tax_payable": {...},
    "tax_payable": {...},
    "cash_paid": {...},
    "itc_utilised": {...}
  },
  "raw": <dict>
}
```

Failure shape when status_cd == "0":
```python
{
  "success": False,
  "status_cd": "0",
  "error_code": <string|None>,
  "message": <string>,
  "raw": <dict>
}
```

### 6.2 get_gstr3b_auto_liability(gstin, year, month)
Endpoint: GET `/gstr-3b/{year}/{month}/auto-liability-calc`

Success return shape:
```python
{
  "success": True,
  "status_cd": <string>,
  "gstin": <string>,
  "auto_calculated_liability": {
    "liab_details": {
      "supply": {...},
      "inter_sup": {...}
    },
    "elg_itc": {...}
  },
  "raw": <dict>
}
```

Failure shape when status_cd == "0":
```python
{
  "success": False,
  "status_cd": "0",
  "error_code": <string|None>,
  "message": <string>,
  "raw": <dict>
}
```

---

## 7) services/gstr_9_service.py

Base URL prefix:
- `{BASE_URL}/gst/compliance/tax-payer/gstrs/gstr-9/...`

Internal helpers:
- _parse_invoice
- _parse_supplier_group

### 7.1 get_gstr9_auto_calculated(gstin, financial_year)
Endpoint: GET `/gstr-9/auto-calculated`

Success return shape:
```python
{
  "success": True,
  "status_cd": <string>,
  "gstin": <string>,
  "financial_period": <string>,
  "aggregate_turnover": <number>,
  "hsn_min_length": <int|None>,
  "table4_outward_supplies": {...},
  "table5_exempt_nil_non_gst": {...},
  "table6_itc_availed": {...},
  "table8_itc_as_per_2b": {...},
  "table9_tax_paid": {...},
  "raw": <dict>
}
```

Failure shape:
```python
{
  "success": False,
  "status_cd": "0",
  "error_code": <string|None>,
  "message": <string>,
  "raw": <dict>
}
```

### 7.2 get_gstr9_table8a(gstin, financial_year, file_number=None)
Endpoint: GET `/gstr-9/table-8a`

Success return shape:
```python
{
  "success": True,
  "status_cd": <string>,
  "gstin": <string>,
  "financial_year": <string>,
  "file_number": <string|int|None>,
  "b2b": [
    {
      "supplier_gstin": <string>,
      "filing_date": <string>,
      "return_period": <string>,
      "documents": [ ...parsed by _parse_invoice... ]
    }
  ],
  "b2ba": [...],
  "cdn": [...],
  "summary": {
    "b2b": {"taxable_value": <number>, "igst": <number>, "cgst": <number>, "sgst": <number>, "cess": <number>, "invoice_count": <int>},
    "b2ba": {...},
    "cdn": {...}
  },
  "raw": <dict>
}
```

Failure shape: same status_cd=="0" pattern.

### 7.3 get_gstr9_details(gstin, financial_year)
Endpoint: GET `/gstr-9`

Success return shape:
```python
{
  "success": True,
  "status_cd": <string>,
  "gstin": <string>,
  "financial_year": <string>,
  "detail_sections": {...},
  "raw": <dict>
}
```

Failure shape:
```python
{"success": False, "message": <string>, "error": <string optional>}
```

---

## 8) services/gst_return_status_service.py

Base URL usage:
- `{BASE_URL}/gst/compliance/tax-payer/gstrs/{year}/{month}/status`

Internal parser family:
- _parse_b2b_errors, _parse_b2cl_errors, _parse_b2cs_errors
- _parse_cdnr_errors, _parse_cdnur_errors, _parse_exp_errors
- _parse_at_txpd_errors, _parse_hsn_errors, _parse_nil_errors
- _parse_doc_issue_errors, _parse_table17_errors
- _parse_error_report

### 8.1 get_gst_return_status(gstin, year, month, reference_id)
Endpoint: GET `/gstrs/{year}/{month}/status?reference_id=...`

Success return shape:
```python
{
  "success": True,
  "status_cd": <string>,
  "form_type": <string>,
  "form_type_label": "GSTR-1"|"GSTR-3B"|"GSTR-9"|<fallback>,
  "action": "SAVE"|"RESET"|<string>,
  "processing_status": "P"|"PE"|"ER"|"REC"|<string>,
  "processing_status_label": <string>,
  "has_errors": <bool>,
  "error_report": {
    ...section-wise normalized error trees...
  },
  "raw": <dict>
}
```

Failure shape (outer status_cd == "0"):
```python
{
  "success": False,
  "status_cd": "0",
  "error_code": <string|None>,
  "message": <string>,
  "raw": <dict>
}
```

---

## 9) services/ledger_service.py

Base URL usage:
- `{BASE_URL}/gst/compliance/tax-payer/ledgers/bal/{year}/{month}`
- `{BASE_URL}/gst/compliance/tax-payer/ledgers/cash`
- `{BASE_URL}/gst/compliance/tax-payer/ledgers/itc`
- `{BASE_URL}/gst/compliance/tax-payer/ledgers/tax/{year}/{month}`

### 9.1 get_cash_itc_balance(gstin, year, month)
Endpoint: GET `/ledgers/bal/{year}/{month}`

Success return shape:
```python
{
  "success": True,
  "status_cd": <string>,
  "gstin": <string>,
  "cash_balance": {
    "igst": {"tax": <number>, "interest": <number>, "penalty": <number>, "fee": <number>, "other": <number>, "total": <number>},
    "cgst": {...},
    "sgst": {...},
    "cess": {...}
  },
  "itc_balance": {"igst": <number>, "cgst": <number>, "sgst": <number>, "cess": <number>},
  "itc_blocked_balance": {"igst": <number>, "cgst": <number>, "sgst": <number>, "cess": <number>},
  "raw": <dict>
}
```

Failure shape: status_cd=="0" error_code/message/raw pattern.

### 9.2 get_cash_ledger(gstin, from_date, to_date)
Endpoint: GET `/ledgers/cash?from=...&to=...`

Success return shape:
```python
{
  "success": True,
  "status_cd": <string>,
  "gstin": <string>,
  "from_date": <string>,
  "to_date": <string>,
  "opening_balance": {...tax-head-wise blocks...},
  "closing_balance": {...tax-head-wise blocks...},
  "transactions": [ ... ],
  "raw": <dict>
}
```

Failure shape: status_cd=="0" error_code/message/raw pattern.

### 9.3 get_itc_ledger(gstin, from_date, to_date)
Endpoint: GET `/ledgers/itc?from=...&to=...`

Success return shape:
```python
{
  "success": True,
  "status_cd": <string>,
  "gstin": <string>,
  "from_date": <string>,
  "to_date": <string>,
  "opening_balance": {
    "igst": <number>,
    "cgst": <number>,
    "sgst": <number>,
    "cess": <number>,
    "total_range_balance": <number>
  },
  "closing_balance": { ...same shape... },
  "transactions": [
    {
      "ref_no": <string>,
      "dt": <string>,
      "ret_period": <string>,
      "desc": <string>,
      "tr_typ": <string>,
      "transaction_amount": {...},
      "balance_after": {...}
    }
  ],
  "provisional_credit_balances": [ ... ],
  "raw": <dict>
}
```

Failure shape: status_cd=="0" error_code/message/raw pattern.

### 9.4 get_return_liability_ledger(gstin, year, month, from_date, to_date)
Endpoint: GET `/ledgers/tax/{year}/{month}?from=...&to=...`

Success return shape:
```python
{
  "success": True,
  "status_cd": <string>,
  "gstin": <string>,
  "from_date": <string>,
  "to_date": <string>,
  "closing_balance": {
    "igst": {...},
    "cgst": {...},
    "sgst": {...},
    "cess": {...}
  },
  "transactions": [
    {
      "ref_no": <string>,
      "dt": <string>,
      "desc": <string>,
      "tr_typ": <string>,
      "dschrg_typ": <string>,
      "tot_tr_amt": <number>,
      "transaction_amount": {...},
      "balance_after": {...}
    }
  ],
  "raw": <dict>
}
```

Failure shape: status_cd=="0" error_code/message/raw pattern.

---

## 10) services/session_refresh_manager.py

Direct BASE_URL call in this file: No
Behavior: indirect API usage via `from services.auth import refresh_session`

Functions:
- _refresh_all_sessions() -> calls refresh_session(gstin)
- _scheduler_loop()
- start_scheduler()
- stop_scheduler()
- manual_refresh(gstin) -> returns refresh_session(gstin)

Return-structure note:
- manual_refresh(gstin) returns exactly the `auth.refresh_session` shape documented in section 2.3.

---

## 11) services/__init__.py

No API-calling functions.
No return structures relevant for DB planner.

---

## 12) Parser Link: parsers/gstr1_parser.py

### parse_gstr1_advance_tax(payload)
Consumed by: services/gstr1_service.py -> get_gstr1_advance_tax

Parser output entity structure (per entry):
```python
{
  "place_of_supply": <string>,
  "supply_type": <string>,
  "items": [
    {
      "rate": <number>,
      "taxable_value": <number>,
      "igst": <number>,
      "cgst": <number>,
      "sgst": <number>,
      "cess": <number>
    }
  ]
}
```

---

## 13) DB Planning Notes (Practical)

Suggested persistence strategy from current service returns:
- Keep one request_audit table for request metadata and upstream_status_code/status_cd/error_code/message.
- Keep one raw_payload table (json) keyed by service/function/gstin/period/reference for traceability.
- Keep normalized fact tables by domain:
  - gstr1_* (b2b, b2cl, cdnr, hsn, nil, txp, etc.)
  - gstr2a_* (b2b, b2ba, cdn, cdna, isd, tds)
  - gstr2b_summary and gstr2b_documents (+ discriminator response_type)
  - gstr3b_details and gstr3b_auto_liability
  - gstr9_auto, gstr9_table8a, gstr9_details
  - gst_return_status + status_error_sections
  - ledger_cash_balance, ledger_cash_txn, ledger_itc_txn, ledger_liability_txn
- Use discriminators for multi-shape functions:
  - gstr2b.get_gstr2b -> response_type (summary/documents) + pagination_required
- Preserve optional/variant keys as nullable columns or JSONB extension columns.

---

## 14) Coverage Checklist

Included services files:
- services/auth.py
- services/gstr1_service.py
- services/gstr_2A_service.py
- services/gstr_2B_service.py
- services/gstr_3B_service.py
- services/gstr_9_service.py
- services/gst_return_status_service.py
- services/ledger_service.py
- services/session_refresh_manager.py
- services/__init__.py

Excluded:
- services/__pycache__/

Document outcome:
- Every API-calling service function with BASE_URL usage is listed with return structures.
- Parser-related return shaping is included where applicable.
