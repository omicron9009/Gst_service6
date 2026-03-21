# SECTION 1 - REPOSITORY ARCHITECTURE

## Executive Summary

This repository is a FastAPI-based GST integration service. It exposes REST endpoints for:

- OTP-based GST session authentication
- GSTR-1
- GSTR-2A
- GSTR-2B
- GSTR-3B
- GSTR-9
- ledger views
- return status lookup

The codebase is organized as flat top-level packages rather than a `backend/` package. There is no top-level `models/`, `utils/`, or `dependencies/` directory. SQLAlchemy models live under `database/`. API routers live under `routers/`. Business logic and upstream API integration live under `services/`. Persistence adapters that convert service responses into ORM rows live under `services/save_db/`.

The application talks to two different backends:

1. Sandbox GST HTTP APIs using `requests`
2. PostgreSQL using SQLAlchemy async + `asyncpg`

The current architecture has a major infrastructure gap:

- The configured PostgreSQL database exists, but the public schema contains zero application tables as of March 14, 2026.
- The repository has ORM models for 34 tables, but no migration system and no schema creation step.

## Repository Tree

```text
Gst_service6/
  .venv/
  database/
    __init__.py
    core/
      __init__.py
      base.py
      config.py
      database.py
    migrations_placeholder/
      README.md
    models/
      __init__.py
      client.py
      session.py
    services/
      __init__.py
      gstr1/
        __init__.py
        models.py
      gstr2a/
        __init__.py
        models.py
      gstr2b/
        __init__.py
        models.py
      gstr3b/
        __init__.py
        models.py
      gstr9/
        __init__.py
        models.py
      gst_return_status/
        __init__.py
        models.py
      ledger/
        __init__.py
        models.py
  frontend/
    db_proxy.py
    gst-api-tester.html
    test_fe.html
  frontend - Copy/
  parsers/
    gstr1_parser.py
  routers/
    __init__.py
    auth_router.py
    gst_r1_router.py
    gst_return_status_router.py
    gstr_2A_router.py
    gstr_2B_router.py
    gstr_3B_router.py
    gstr_9_router.py
    ledger_router.py
  schemas/
    gstr1.py
  services/
    __init__.py
    auth.py
    gst_return_status_service.py
    gstr1_service.py
    gstr_2A_service.py
    gstr_2B_service.py
    gstr_3B_service.py
    gstr_9_service.py
    ledger_service.py
    session_refresh_manager.py
    save_db/
      __init__.py
      base_saver.py
      save_auth.py
      save_gstr1.py
      save_gstr2a.py
      save_gstr2b.py
      save_gstr3b.py
      save_gstr9.py
      save_ledger.py
      save_return_status.py
  sessions/
    27AABFP2335E1ZM_session.json
  config.py
  main.py
  session_storage.py
  smoke_auth.db
  smoke_auth_persistence.py
```

## File Role Map

### Application entrypoint

- `main.py`
  - creates `FastAPI` app
  - installs permissive CORS middleware
  - registers all routers
  - runs startup lifespan
  - startup calls `ensure_database_exists()`
  - startup starts background session refresh thread

### Global config

- `config.py`
  - external Sandbox API config
  - currently contains hardcoded API key, secret, default GSTIN, default username

### Session state

- `session_storage.py`
  - in-memory plus JSON-file session store under `sessions/`
  - exported functions:
    - `save_session`
    - `get_session`
    - `get_all_sessions`
    - `delete_session`

- `services/session_refresh_manager.py`
  - background thread that refreshes stored GST sessions every 5h30m
  - exported functions:
    - `start_scheduler`
    - `stop_scheduler`
    - `manual_refresh`

### Routers

- `routers/auth_router.py`
  - OTP/session endpoints
  - inline Pydantic request models: `OTPGenerate`, `OTPVerify`, `RefreshRequest`

- `routers/gst_r1_router.py`
  - GSTR-1 routes

- `routers/gstr_2A_router.py`
  - GSTR-2A routes

- `routers/gstr_2B_router.py`
  - GSTR-2B routes

- `routers/gstr_3B_router.py`
  - GSTR-3B routes

- `routers/gstr_9_router.py`
  - GSTR-9 routes

- `routers/ledger_router.py`
  - ledger routes

- `routers/gst_return_status_router.py`
  - return status route

### Schemas

- `schemas/gstr1.py`
  - `Gstr1RequestInfo`
  - `Gstr1AdvanceItem`
  - `Gstr1AdvanceEntry`
  - `Gstr1AdvanceTaxResponse`
  - Only GSTR-1 advance-tax has an explicit response model in OpenAPI.

### Service layer

- `services/auth.py`
  - OTP generation
  - OTP verification
  - session refresh
  - platform authentication against `/authenticate`
  - writes sessions to JSON store and PostgreSQL

- `services/gstr1_service.py`
  - all GSTR-1 upstream calls and normalization

- `services/gstr_2A_service.py`
  - all GSTR-2A upstream calls and normalization

- `services/gstr_2B_service.py`
  - all GSTR-2B upstream calls and normalization

- `services/gstr_3B_service.py`
  - all GSTR-3B upstream calls and normalization

- `services/gstr_9_service.py`
  - all GSTR-9 upstream calls and normalization

- `services/ledger_service.py`
  - balance and ledger upstream calls and normalization

- `services/gst_return_status_service.py`
  - status lookup and error report parsing

### Persistence layer

- `services/save_db/base_saver.py`
  - generic coercion helpers
  - client creation
  - bulk insert helpers
  - transaction wrapper

- `services/save_db/save_auth.py`
  - persists auth session into `clients` and `gst_sessions`

- `services/save_db/save_gstr1.py`
  - persists GSTR-1 outputs into GSTR-1 model tables

- `services/save_db/save_gstr2a.py`
  - persists GSTR-2A outputs into GSTR-2A model tables

- `services/save_db/save_gstr2b.py`
  - persists GSTR-2B outputs into GSTR-2B model tables

- `services/save_db/save_gstr3b.py`
  - persists GSTR-3B outputs into GSTR-3B model tables

- `services/save_db/save_gstr9.py`
  - persists GSTR-9 outputs into GSTR-9 model tables

- `services/save_db/save_ledger.py`
  - persists ledger outputs into ledger model tables

- `services/save_db/save_return_status.py`
  - persists return status outputs into return status table

### Database core

- `database/core/base.py`
  - SQLAlchemy declarative base and common mixins

- `database/core/config.py`
  - database settings source
  - currently hardcodes PostgreSQL DSN instead of reading env

- `database/core/database.py`
  - async engine
  - async sessionmaker
  - `get_db`
  - `ensure_database_exists`

### ORM models

- `database/models/client.py`
  - `Client`

- `database/models/session.py`
  - `GstSession`

- `database/services/*/models.py`
  - domain-specific SQLAlchemy models for GSTR1, GSTR2A, GSTR2B, GSTR3B, GSTR9, ledger, return status

### Utilities and tests

- `parsers/gstr1_parser.py`
  - parser for GSTR-1 advance-tax payload shape

- `smoke_auth_persistence.py`
  - smoke test using patched auth HTTP responses and `TestClient`
  - intended to verify OTP -> session persistence flow

- `frontend/db_proxy.py`
  - development-only SQL-over-HTTP proxy for DB inspection

- `frontend/gst-api-tester.html`
  - manual API tester and DB browser UI


# SECTION 2 - API ENDPOINT MAP

## Authentication and Session

- `POST /auth/generate-otp`
  - router: `routers.auth_router.generate_otp_route`
  - service: `services.auth.generate_otp`
  - request schema: `OTPGenerate { username: str, gstin: str }`
  - response schema: untyped JSON dict
  - auth requirement: none
  - DB usage: none directly; no DB write until verify

- `POST /auth/verify-otp`
  - router: `routers.auth_router.verify_otp_route`
  - service: `services.auth.verify_otp`
  - request schema: `OTPVerify { username: str, gstin: str, otp: str }`
  - response schema: untyped JSON dict
  - auth requirement: none
  - DB usage: writes `clients` and `gst_sessions` via `save_auth_session_to_db`; also writes JSON session file

- `POST /auth/refresh`
  - router: `routers.auth_router.refresh_session_route`
  - service: `services.auth.refresh_session`
  - request schema: `RefreshRequest { gstin: str }`
  - response schema: untyped JSON dict
  - auth requirement: active GST session for GSTIN in JSON session store
  - DB usage: updates `gst_sessions`; also updates JSON session file

- `GET /auth/session/{gstin}`
  - router: `routers.auth_router.get_session_status`
  - service dependency: `session_storage.get_session`
  - request schema: path `gstin`
  - response schema: untyped JSON dict
  - auth requirement: none
  - DB usage: none; only JSON/in-memory session storage

## GSTR-1

- `GET /gstr1/advance-tax/{gstin}/{year}/{month}`
  - service: `get_gstr1_advance_tax`
  - request params: path `gstin`, `year`, `month`
  - response schema: `Gstr1AdvanceTaxResponse`
  - auth requirement: active GST session
  - DB usage: `save_gstr1_to_db` -> `gstr1_advance_tax_records`

- `GET /gstr1/b2b/{gstin}/{year}/{month}`
  - service: `get_gstr1_b2b`
  - query params: `action_required`, `from_date`, `counterparty_gstin`
  - response schema: untyped JSON dict
  - auth requirement: active GST session
  - DB usage: `gstr1_b2b_records`

- `GET /gstr1/summary/{gstin}/{year}/{month}`
  - service: `get_gstr1_summary`
  - query params: `summary_type=short|long`
  - response schema: untyped JSON dict
  - auth requirement: active GST session
  - DB usage: `gstr1_summary_records`

- `GET /gstr1/b2csa/{gstin}/{year}/{month}`
  - service: `get_gstr1_b2csa`
  - DB usage: `gstr1_b2csa_records`

- `GET /gstr1/b2cs/{gstin}/{year}/{month}`
  - service: `get_gstr1_b2cs`
  - DB usage: `gstr1_b2cs_records`

- `GET /gstr1/cdnr/{gstin}/{year}/{month}`
  - service: `get_gstr1_cdnr`
  - query params: `action_required`, `from`
  - DB usage: `gstr1_cdnr_records`

- `GET /gstr1/doc-issue/{gstin}/{year}/{month}`
  - service: `get_gstr1_doc_issue`
  - DB usage: `gstr1_doc_issue_records`

- `GET /gstr1/hsn/{gstin}/{year}/{month}`
  - service: `get_gstr1_hsn`
  - DB usage: `gstr1_hsn_records`

- `GET /gstr1/nil/{gstin}/{year}/{month}`
  - service: `get_gstr1_nil`
  - DB usage: `gstr1_nil_records`

- `GET /gstr1/b2cl/{gstin}/{year}/{month}`
  - service: `get_gstr1_b2cl`
  - query params: `state_code`
  - DB usage: `gstr1_b2cl_records`

- `GET /gstr1/cdnur/{gstin}/{year}/{month}`
  - service: `get_gstr1_cdnur`
  - DB usage: `gstr1_cdnur_records`

- `GET /gstr1/exp/{gstin}/{year}/{month}`
  - service: `get_gstr1_exp`
  - DB usage: `gstr1_exp_records`

- `GET /gstr1/gstr1/{gstin}/{year}/{month}/txp`
  - service: `get_gstr1_txp`
  - query params: `counterparty_gstin`, `action_required`, `from`
  - DB usage: `gstr1_txp_records`
  - note: duplicated `gstr1` path segment is part of current route contract

## GSTR-2A

- `GET /gstr2A/b2b/{gstin}/{year}/{month}`
  - service: `get_gstr2a_b2b`
  - DB usage: `gstr2a_b2b_records`

- `GET /gstr2A/b2ba/{gstin}/{year}/{month}`
  - service: `get_gstr2a_b2ba`
  - query params: `counterparty_gstin`
  - DB usage: `gstr2a_b2ba_records`

- `GET /gstr2A/cdn/{gstin}/{year}/{month}`
  - service: `get_gstr2a_cdn`
  - query params: `counterparty_gstin`, `from_date`
  - DB usage: `gstr2a_cdn_records`

- `GET /gstr2A/cdna/{gstin}/{year}/{month}`
  - service: `get_gstr2a_cdna`
  - query params: `counterparty_gstin`
  - DB usage: `gstr2a_cdna_records`

- `GET /gstr2A/document/{gstin}/{year}/{month}`
  - service: `get_gstr2a_document`
  - DB usage: `gstr2a_document_records`, plus section tables depending on response shape

- `GET /gstr2A/isd/{gstin}/{year}/{month}`
  - service: `get_gstr2a_isd`
  - query params: `counterparty_gstin`
  - DB usage: `gstr2a_isd_records`

- `GET /gstr2A/gstr2a/{gstin}/{year}/{month}/tds`
  - service: `get_gstr2a_tds`
  - DB usage: `gstr2a_tds_records`
  - note: mixed-case duplicate `gstr2A/gstr2a` path shape is part of current route contract

## GSTR-2B

- `GET /gstr2B/gstr2b/{gstin}/{year}/{month}`
  - service: `get_gstr2b`
  - query params: `file_number`
  - DB usage: `gstr2b_records`

- `GET /gstr2B/gstr2b/{gstin}/regenerate/status`
  - service: `get_gstr2b_regeneration_status`
  - query params: `reference_id`
  - DB usage: `gstr2b_regeneration_status_records`

## GSTR-3B

- `GET /gstr3B/gstr3b/{gstin}/{year}/{month}`
  - service: `get_gstr3b_details`
  - DB usage: `gstr3b_details_records`

- `GET /gstr3B/gstr3b/{gstin}/{year}/{month}/auto-liability-calc`
  - service: `get_gstr3b_auto_liability`
  - DB usage: `gstr3b_auto_liability_records` and also `gstr3b_details_records` due current saver behavior

## GSTR-9

- `GET /gstr9/gstr9/{gstin}/auto-calculated`
  - service: `get_gstr9_auto_calculated`
  - query params: `financial_year`
  - DB usage: `gstr9_auto_calculated_records`

- `GET /gstr9/gstr9/{gstin}/table-8a`
  - service: `get_gstr9_table8a`
  - query params: `financial_year`, `file_number`
  - DB usage: `gstr9_table8a_records`

- `GET /gstr9/gstr9/{gstin}`
  - service: `get_gstr9_details`
  - query params: `financial_year`
  - DB usage: `gstr9_details_records`

## Ledgers

- `GET /ledgers/ledgers/{gstin}/{year}/{month}/balance`
  - service: `get_cash_itc_balance`
  - DB usage: `ledger_cash_itc_balance_records`
  - note: duplicated `ledgers/ledgers` path segment is part of current route contract

- `GET /ledgers/ledgers/{gstin}/cash`
  - service: `get_cash_ledger`
  - query params: `from`, `to`
  - DB usage: intended `ledger_cash_ledger_records`, but current saver also inserts into ITC and liability ledger tables

- `GET /ledgers/ledgers/{gstin}/itc`
  - service: `get_itc_ledger`
  - query params: `from`, `to`
  - DB usage: intended `ledger_itc_ledger_records`, but current saver also inserts into cash and liability ledger tables

- `GET /ledgers/ledgers/{gstin}/tax/{year}/{month}`
  - service: `get_return_liability_ledger`
  - query params: `from`, `to`
  - DB usage: intended `ledger_return_liability_ledger_records`, but current saver also inserts into cash and ITC ledger tables

## Return Status

- `GET /return_status/returns/{gstin}/{year}/{month}/status`
  - service: `get_gst_return_status`
  - query params: `reference_id`
  - DB usage: `gst_return_status_records`

## Utility

- `GET /health`
  - returns `{"status": "ok"}`
  - no auth
  - no DB usage


# SECTION 3 - SERVICE LAYER MAP

## Service-to-model map

- `generate_otp`
  - purpose: trigger GST OTP send
  - upstream: `POST {BASE_URL}/gst/compliance/tax-payer/otp`
  - models accessed: none

- `verify_otp`
  - purpose: verify OTP and save GST access tokens
  - upstream: `POST {BASE_URL}/gst/compliance/tax-payer/otp/verify?otp=...`
  - models accessed: `Client`, `GstSession`
  - persistence: `save_auth_session_to_db`

- `refresh_session`
  - purpose: refresh GST taxpayer session
  - upstream: `POST {BASE_URL}/gst/compliance/tax-payer/session/refresh`
  - models accessed: `Client`, `GstSession`
  - persistence: `save_auth_session_to_db`

- `get_gstr1_advance_tax`
  - purpose: fetch normalized advance tax rows
  - model: `Gstr1AdvanceTaxRecord`

- `get_gstr1_b2b`
  - purpose: fetch normalized B2B invoices
  - model: `Gstr1B2BRecord`

- `get_gstr1_summary`
  - purpose: fetch short or long summary sections
  - model: `Gstr1SummaryRecord`

- `get_gstr1_b2csa`
  - model: `Gstr1B2CSARecord`

- `get_gstr1_b2cs`
  - model: `Gstr1B2CSRecord`

- `get_gstr1_cdnr`
  - model: `Gstr1CDNRRecord`

- `get_gstr1_doc_issue`
  - model: `Gstr1DocIssueRecord`

- `get_gstr1_hsn`
  - model: `Gstr1HSNRecord`

- `get_gstr1_nil`
  - model: `Gstr1NilRecord`

- `get_gstr1_b2cl`
  - model: `Gstr1B2CLRecord`

- `get_gstr1_cdnur`
  - model: `Gstr1CDNURRecord`

- `get_gstr1_exp`
  - model: `Gstr1EXPRecord`

- `get_gstr1_txp`
  - model: `Gstr1TXPRecord`

- `get_gstr2a_b2b`
  - model: `Gstr2AB2BRecord`

- `get_gstr2a_b2ba`
  - model: `Gstr2AB2BARecord`

- `get_gstr2a_cdn`
  - model: `Gstr2ACDNRecord`

- `get_gstr2a_cdna`
  - model: `Gstr2ACDNARecord`

- `get_gstr2a_document`
  - primary model: `Gstr2ADocumentRecord`
  - also persisted into section tables for `b2b`, `b2ba`, `cdn` when those arrays exist

- `get_gstr2a_isd`
  - model: `Gstr2AISDRecord`

- `get_gstr2a_tds`
  - model: `Gstr2ATDSRecord`

- `get_gstr2b`
  - model: `Gstr2BRecord`
  - behavior:
    - parses summary-only response shapes
    - parses document-heavy response shapes
    - stores document rows and pagination metadata

- `get_gstr2b_regeneration_status`
  - model: `Gstr2BRegenerationStatusRecord`

- `get_gstr3b_details`
  - model: `Gstr3BDetailsRecord`

- `get_gstr3b_auto_liability`
  - model: `Gstr3BAutoLiabilityRecord`

- `get_gstr9_auto_calculated`
  - model: `Gstr9AutoCalculatedRecord`

- `get_gstr9_table8a`
  - model: `Gstr9Table8ARecord`

- `get_gstr9_details`
  - model: `Gstr9DetailsRecord`

- `get_cash_itc_balance`
  - model: `LedgerCashItcBalanceRecord`

- `get_cash_ledger`
  - intended model: `LedgerCashLedgerRecord`

- `get_itc_ledger`
  - intended model: `LedgerItcLedgerRecord`

- `get_return_liability_ledger`
  - intended model: `LedgerReturnLiabilityLedgerRecord`

- `get_gst_return_status`
  - model: `GstReturnStatusRecord`

## Transaction handling

- Database writes are isolated in `services/save_db/*`.
- `run_persistence()` opens `AsyncSessionLocal`, runs a callback, then commits.
- Any connectivity or SQLAlchemy error is swallowed and logged; API responses still return success if upstream API succeeded.
- There is no explicit rollback logic in `run_persistence()` because session context manager cleanup handles failed transactions implicitly.

## Dependency injection usage

- `database.core.database.get_db` exists but is not used by routers or services.
- Database access is not injected into route handlers.
- Services call persistence functions directly; persistence functions instantiate their own async sessions.

## Async usage

- Nearly all business functions are declared `async`.
- All upstream HTTP calls use synchronous `requests.get()` / `requests.post()`.
- This blocks the event loop under load and is a backend integration concern.


# SECTION 4 - DATABASE MODELS

## Common mixins

- `PrimaryKeyMixin`
  - `id` integer PK

- `TimestampMixin`
  - `created_at` timestamp with timezone, server default `now()`
  - `updated_at` timestamp with timezone, server default `now()`, onupdate `now()`

- `ClientScopeMixin`
  - `client_id` FK -> `clients.id`, indexed, not null
  - `gstin` varchar(15), indexed, not null

- `MonthlyPeriodMixin`
  - `year` smallint, indexed, nullable
  - `month` smallint, indexed, nullable

- `FinancialYearMixin`
  - `financial_year` varchar(9), indexed, nullable

- `DateRangeMixin`
  - `from_date` date, indexed, nullable
  - `to_date` date, indexed, nullable

- `RawPayloadMixin`
  - `raw_payload` JSONB, not null

- `JsonRecordMixin`
  - `record_payload` JSONB, nullable

- `TaxAmountsMixin`
  - `taxable_value` numeric(18,2)
  - `tax_rate` numeric(7,3)
  - `igst` numeric(18,2)
  - `cgst` numeric(18,2)
  - `sgst` numeric(18,2)
  - `cess` numeric(18,2)

## Base entities

- `clients`
  - columns: `id`, `gstin` unique indexed not null, `legal_name`, `created_at`, `updated_at`

- `gst_sessions`
  - columns: `id`, `client_id`, `access_token`, `refresh_token`, `username`, `token_expiry`, `session_expiry`, `last_refresh`, `created_at`, `updated_at`
  - relationship: many sessions belong to one `Client`

## GSTR-1 tables

All GSTR-1 tables include:

- `id`, `client_id`, `gstin`, `year`, `month`, `raw_payload`, `created_at`, `updated_at`

Specific tables:

- `gstr1_advance_tax_records`
  - `place_of_supply`, `supply_type`, `advance_amount`, `tax_rate`, `cgst`, `sgst`, `cess`

- `gstr1_b2b_records`
  - `counterparty_gstin`, `invoice_number`, `invoice_date`, `place_of_supply`, `invoice_type`, `reverse_charge`, `invoice_value`, tax amount fields

- `gstr1_summary_records`
  - `section_name`, `checksum`, `counterparties` JSONB, `sub_sections` JSONB, `record_payload` JSONB

- `gstr1_b2csa_records`
  - `place_of_supply`, `supply_type`, `invoice_type`, tax amount fields

- `gstr1_b2cs_records`
  - `place_of_supply`, `supply_type`, `invoice_type`, `checksum`, `flag`, tax amount fields

- `gstr1_cdnr_records`
  - `counterparty_gstin`, `counter_filing_status`, `note_number`, `note_date`, `note_type`, `invoice_type`, `place_of_supply`, `reverse_charge`, `note_value`, `flag`, `delete_flag`, `updated_by`, `checksum`, `item_number`, tax amount fields

- `gstr1_doc_issue_records`
  - `document_type_number`, `serial_number`, `from_serial`, `to_serial`, `total_issued`, `cancelled`, `net_issued`

- `gstr1_hsn_records`
  - `serial_number`, `hsn_sac_code`, `description`, `unit_of_quantity`, `quantity`, tax amount fields

- `gstr1_nil_records`
  - `supply_type_code`, `supply_type`, `nil_rated_amount`, `exempted_amount`, `non_gst_amount`

- `gstr1_b2cl_records`
  - `place_of_supply`, `invoice_number`, `invoice_date`, `invoice_value`, `flag`, `item_number`, tax amount fields

- `gstr1_cdnur_records`
  - `note_number`, `note_date`, `note_type_code`, `note_type`, `supply_type_code`, `supply_type`, `note_value`, `flag`, `delete_flag`, `item_number`, tax amount fields

- `gstr1_exp_records`
  - `export_type_code`, `export_type`, `invoice_number`, `invoice_date`, `invoice_value`, `flag`, `item_number`, tax amount fields

- `gstr1_txp_records`
  - `place_of_supply`, `supply_type`, `flag`, `action_required`, `checksum`, `item_number`, `advance_amount`, `tax_rate`, `igst`, `cgst`, `sgst`, `cess`

## GSTR-2A tables

All GSTR-2A tables include:

- `id`, `client_id`, `gstin`, `year`, `month`, `raw_payload`, `created_at`, `updated_at`

Specific tables:

- `gstr2a_b2b_records`
  - supplier status fields, invoice fields, `place_of_supply`, `reverse_charge`, `source_type`, `irn`, `irn_gen_date`, `item_number`, tax amount fields

- `gstr2a_b2ba_records`
  - supplier status fields, invoice fields, original invoice fields, amendment fields, `place_of_supply`, `reverse_charge`, `item_number`, tax amount fields

- `gstr2a_cdn_records`
  - supplier status fields, note fields, `invoice_type`, `note_value`, `place_of_supply`, `reverse_charge`, `delete_flag`, `source_type`, `irn`, `irn_gen_date`, `item_number`, tax amount fields

- `gstr2a_cdna_records`
  - `supplier_gstin`, `filing_status_gstr1`, note fields, original note fields, invoice fields, `invoice_type`, `note_value`, `place_of_supply`, `reverse_charge`, `delete_flag`, `diff_percent`, `pre_gst`, `item_number`, tax amount fields

- `gstr2a_document_records`
  - `section`, supplier status fields, invoice fields, original invoice fields, amendment fields, note fields, `invoice_type`, `invoice_value`, `note_value`, `place_of_supply`, `reverse_charge`, `delete_flag`, `source_type`, `irn`, `irn_gen_date`, `item_number`, tax amount fields

- `gstr2a_isd_records`
  - `distributor_gstin`, `filing_status_gstr1`, `document_number`, `document_date`, `document_type_code`, `document_type`, `itc_eligible`, `igst`, `cgst`, `sgst`, `cess`

- `gstr2a_tds_records`
  - `deductor_name`, `deductor_gstin`, `recipient_gstin`, `return_period`, `deduction_base_amount`, `igst`, `cgst`, `sgst`

## GSTR-2B tables

All GSTR-2B tables include:

- `id`, `client_id`, `gstin`, `year`, `month`, `raw_payload`, `created_at`, `updated_at`

Specific tables:

- `gstr2b_records`
  - `status_cd`, `response_type`, `file_count`, `file_number`, `section`
  - supplier fields
  - invoice/original invoice fields
  - note/original note fields
  - document fields
  - `place_of_supply`, `invoice_type`, `reverse_charge`, `itc_available`, `diff_percent`
  - tax/value fields
  - `source_type`, `ims_status`, `reason`, `irn`, `irn_gen_date`, `item_number`
  - `record_payload`

- `gstr2b_regeneration_status_records`
  - `reference_id` indexed not null
  - `regeneration_status`, `regeneration_status_label`, `error_code`, `error_message`

## GSTR-3B tables

All GSTR-3B tables include:

- `id`, `client_id`, `gstin`, `year`, `month`, `raw_payload`, `created_at`, `updated_at`

Specific tables:

- `gstr3b_details_records`
  - `section` not null
  - `subsection`, `line_code`, `line_label`
  - `place_of_supply`, `transaction_type`, `transaction_description`, `liability_ledger_id`
  - tax and amount fields
  - `record_payload`

- `gstr3b_auto_liability_records`
  - `section` not null
  - `subsection`, `source_table`, `place_of_supply`
  - tax fields
  - `record_payload`

## GSTR-9 tables

All GSTR-9 tables include:

- `id`, `client_id`, `gstin`, `financial_year`, `raw_payload`, `created_at`, `updated_at`

Shared line fields include:

- `table_code` indexed
- `section_code`
- `section_label`
- supplier and return metadata fields
- invoice/original invoice/note fields
- `invoice_type`, `place_of_supply`, `reverse_charge`
- `hsn_sac`, `description`, `is_concessional`
- tax/value/payment fields

Specific tables:

- `gstr9_auto_calculated_records`
  - shared line fields + `record_payload`

- `gstr9_table8a_records`
  - shared line fields + `file_number`, `is_eligible`, `ineligibility_reason`

- `gstr9_details_records`
  - shared line fields + `record_payload`

## Ledger tables

All ledger tables include:

- `id`, `client_id`, `gstin`, `raw_payload`, `created_at`, `updated_at`

Specific tables:

- `ledger_cash_itc_balance_records`
  - `year`, `month`
  - `snapshot_type`, `tax_head`, `component`, `amount`

- `ledger_cash_ledger_records`
  - `from_date`, `to_date`
  - `entry_type`, `transaction_reference`, `transaction_date`, `description`, `transaction_type`, `discharge_type`, `tax_head`, `component`, `amount`, `balance_amount`, `total_transaction_amount`, `total_range_balance`, `record_payload`

- `ledger_itc_ledger_records`
  - `from_date`, `to_date`
  - `entry_type`, `transaction_reference`, `transaction_date`, `return_period`, `description`, `transaction_type`, `tax_head`, `amount`, `balance_after`, `total_transaction_amount`, `total_range_balance`, `record_payload`

- `ledger_return_liability_ledger_records`
  - `year`, `month`, `from_date`, `to_date`
  - `entry_type`, `transaction_reference`, `transaction_date`, `description`, `transaction_type`, `discharge_type`, `tax_head`, `component`, `amount`, `balance_after`, `total_transaction_amount`, `total_range_balance_after`, `record_payload`

## Return status table

- `gst_return_status_records`
  - common columns: `id`, `client_id`, `gstin`, `year`, `month`, `raw_payload`, `created_at`, `updated_at`
  - specific columns:
    - `reference_id` indexed not null
    - `status_cd`
    - `form_type`
    - `form_type_label`
    - `action`
    - `processing_status`
    - `processing_status_label`
    - `has_errors`
    - `error_code`
    - `error_message`
    - `error_report` JSONB


# SECTION 5 - DATABASE SCHEMA

## Expected schema from ORM metadata

Expected public tables: 34

- `clients`
- `gst_sessions`
- `gst_return_status_records`
- `gstr1_advance_tax_records`
- `gstr1_b2b_records`
- `gstr1_b2cl_records`
- `gstr1_b2cs_records`
- `gstr1_b2csa_records`
- `gstr1_cdnr_records`
- `gstr1_cdnur_records`
- `gstr1_doc_issue_records`
- `gstr1_exp_records`
- `gstr1_hsn_records`
- `gstr1_nil_records`
- `gstr1_summary_records`
- `gstr1_txp_records`
- `gstr2a_b2b_records`
- `gstr2a_b2ba_records`
- `gstr2a_cdn_records`
- `gstr2a_cdna_records`
- `gstr2a_document_records`
- `gstr2a_isd_records`
- `gstr2a_tds_records`
- `gstr2b_records`
- `gstr2b_regeneration_status_records`
- `gstr3b_auto_liability_records`
- `gstr3b_details_records`
- `gstr9_auto_calculated_records`
- `gstr9_details_records`
- `gstr9_table8a_records`
- `ledger_cash_itc_balance_records`
- `ledger_cash_ledger_records`
- `ledger_itc_ledger_records`
- `ledger_return_liability_ledger_records`

## Actual database state

Validated on March 14, 2026 against:

- `postgresql+asyncpg://postgres:root@localhost:5432/gst_platform`

Observed public tables: 0

Result:

- Every expected application table is missing.
- There is no `alembic_version` table.
- There are no partial schema objects to compare for column or index mismatches.

## Schema validation conclusion

The main DB failure is not a column mismatch. It is total schema absence.

Most likely first failing insert path:

- `save_auth_session_to_db()` calls `get_or_create_client_id()`
- `get_or_create_client_id()` queries `clients`
- because `clients` does not exist, PostgreSQL will raise an undefined-table error

All domain persistence tables are similarly absent.


# SECTION 6 - DATABASE CONNECTION DETAILS

## Configured connection chain

PostgreSQL
-> `asyncpg`
-> SQLAlchemy `AsyncEngine`
-> SQLAlchemy `AsyncSession`
-> persistence functions in `services/save_db/*`

## Engine and session configuration

- engine factory: `create_async_engine(settings.database_url, echo=settings.echo_sql, future=True, pool_pre_ping=True)`
- session factory: `async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False)`
- dependency helper: `get_db()`
- actual usage pattern: direct session creation inside persistence functions, not FastAPI dependency injection

## Database URL

Configured in code:

- `postgresql+asyncpg://postgres:root@localhost:5432/gst_platform`

Important finding:

- `database/core/config.py` does not read `DATABASE_URL` from environment.
- The settings object is effectively hardcoded.

## Startup DB behavior

Startup runs `ensure_database_exists()`:

- if DSN is PostgreSQL, it attempts to connect to the target DB
- if target DB is missing, it connects to admin DB and issues `CREATE DATABASE`
- it does not create tables
- it does not run migrations
- it does not call `Base.metadata.create_all()`

## Session lifecycle

- `get_db()` exists but is unused in routes/services
- persistence functions use `AsyncSessionLocal()` ad hoc
- each persistence operation commits once at the end of the callback
- API read paths do not read from PostgreSQL; they read from JSON session storage


# SECTION 7 - DETECTED INFRASTRUCTURE ISSUES

## Critical

1. No schema creation or migration path exists.
   - `ensure_database_exists()` creates only the database, not tables.
   - PostgreSQL currently contains zero application tables.

2. Migrations are missing.
   - Only `database/migrations_placeholder/README.md` exists.
   - There is no Alembic setup, no versions, no migration history.

3. Database configuration is hardcoded.
   - `database/core/config.py` ignores environment variables.
   - This makes deployment and testing brittle.

4. Secrets are committed in source.
   - `config.py` contains a live-looking API key and API secret.
   - It also contains a default GSTIN and username.

5. Persistence failures are intentionally swallowed.
   - `run_persistence()` logs connectivity/SQLAlchemy errors and returns.
   - Upstream API calls can succeed while DB persistence silently fails.

## High

6. Async services use blocking `requests`.
   - Every upstream HTTP integration uses synchronous I/O inside `async def`.
   - This can block the event loop and reduce throughput.

7. Auth/session state is split between JSON files and PostgreSQL.
   - Runtime auth checks use `session_storage.get_session()`.
   - Postgres `gst_sessions` is written, but not used as the runtime source of truth.
   - App restart recovery depends on JSON files, not DB rows.

8. API auth requirements are hidden from OpenAPI.
   - Protected routes rely on stored GST session presence, not FastAPI security dependencies.
   - OpenAPI reports no security requirements for protected routes.

9. Several route paths have duplicated segments.
   - `/gstr1/gstr1/{gstin}/{year}/{month}/txp`
   - `/gstr2A/gstr2a/{gstin}/{year}/{month}/tds`
   - `/gstr9/gstr9/{gstin}/...`
   - `/ledgers/ledgers/{gstin}/...`
   - Frontend generation must use exact paths as implemented, even if they look wrong.

## Medium

10. `save_ledger_to_db()` cross-populates unrelated ledger tables.
    - Any `transactions` list is inserted into cash, ITC, and liability tables in the same call.
    - This will contaminate persisted ledger data if schema is created.

11. `save_gstr3b_to_db()` duplicates auto-liability data.
    - `auto_liability` is included in detail rows and then inserted again into auto-liability rows.

12. `save_gstr2a_to_db()` has ambiguous document persistence.
    - `document` endpoint persistence depends on `b2b`, `b2ba`, `cdn` arrays being present.
    - If the upstream document shape changes, records may be partially persisted or duplicated.

13. GSTIN normalization is inconsistent in DB persistence.
    - `session_storage` uppercases GSTIN.
    - `get_or_create_client_id()` only strips whitespace.

14. Smoke test environment override is misleading.
    - `smoke_auth_persistence.py` sets `DATABASE_URL` to SQLite.
    - Current DB settings ignore it, so the test is not truly portable.

15. `frontend/db_proxy.py` is a major security risk if exposed.
    - It executes arbitrary SQL over HTTP.
    - CORS defaults to `*`.
    - Writes are allowed unless `--readonly` is explicitly passed.


# SECTION 8 - MIGRATION STATUS

## Current status

- No Alembic project
- No `alembic.ini`
- No `alembic/`
- No `migrations/versions/`
- Only placeholder docs exist

## Required initial migration scope

Initial migration must create all 34 ORM tables plus indexes and foreign keys:

- `clients`
- `gst_sessions`
- all GSTR-1 tables
- all GSTR-2A tables
- all GSTR-2B tables
- all GSTR-3B tables
- all GSTR-9 tables
- all ledger tables
- `gst_return_status_records`

## Migration recommendation

Use Alembic with:

- `target_metadata` wired to imported ORM metadata
- safe import path that loads all models, not only `Base`
- first migration generated from current ORM tables


# SECTION 9 - FULL SYSTEM CONTEXT PROMPT FOR AI

```text
You are working on a production FastAPI GST backend. Your task is to understand the backend exactly as implemented and use that understanding to build a frontend dashboard and repair backend integrations without changing business meaning unless explicitly requested.

SYSTEM OVERVIEW

- Runtime: FastAPI
- Primary app file: main.py
- Architecture style: flat top-level modules, not a backend/ package
- External integration: Sandbox GST HTTP APIs
- Persistence: PostgreSQL via SQLAlchemy async + asyncpg
- Session state: duplicated across JSON files and PostgreSQL

TOP-LEVEL REPOSITORY LAYOUT

- main.py -> FastAPI app bootstrap, router registration, CORS, startup lifespan
- config.py -> Sandbox API config, currently hardcoded credentials and default GSTIN/username
- session_storage.py -> JSON and in-memory GST session store
- routers/ -> FastAPI route modules
- services/ -> business logic and upstream HTTP integrations
- services/save_db/ -> persistence adapters from normalized service output into ORM rows
- schemas/ -> small Pydantic schema layer, currently only GSTR-1 advance-tax is fully typed
- database/core/ -> SQLAlchemy base, settings, engine, sessionmaker
- database/models/ -> core auth/session tables
- database/services/*/models.py -> domain ORM tables
- frontend/ -> dev/test HTML UI and DB proxy
- parsers/ -> parser utility for GSTR-1 advance-tax

ROUTER REGISTRATION

The app includes these routers:

- auth_router
- gst_r1_router
- gstr_2A_router
- gstr_2B_router
- gstr_3B_router
- gstr_9_router
- ledger_router
- gst_return_status_router

AUTHENTICATION MODEL

This backend does NOT use FastAPI OAuth/security dependencies.

Instead:

1. Client calls POST /auth/generate-otp with username + GSTIN
2. Client calls POST /auth/verify-otp with username + GSTIN + OTP
3. Service stores GST access token in:
   - JSON file under sessions/<GSTIN>_session.json
   - PostgreSQL table gst_sessions
4. All GST data endpoints later call session_storage.get_session(gstin)
5. If no active session exists in JSON/in-memory storage, the service returns a business error like:
   - {"success": false, "message": "GST session not found"}

Important implication:

- The runtime source of truth for auth is JSON/in-memory, not PostgreSQL.
- OpenAPI shows no security requirements even for protected routes.

DATABASE CONNECTION DETAILS

- SQLAlchemy async engine is created in database/core/database.py
- DSN is currently hardcoded in database/core/config.py as:
  postgresql+asyncpg://postgres:root@localhost:5432/gst_platform
- engine options:
  - echo from settings.echo_sql
  - future=True
  - pool_pre_ping=True
- Async sessionmaker:
  - expire_on_commit=False
  - autoflush=False
  - autocommit=False

DATABASE STATUS AS OF MARCH 14, 2026

- Connected successfully to PostgreSQL at localhost:5432/gst_platform
- Public schema contains zero application tables
- ORM metadata expects 34 tables
- No alembic_version table exists
- Therefore the current primary infrastructure bug is total schema absence

SCHEMA CREATION GAP

Startup currently calls ensure_database_exists(), which:

- checks whether the PostgreSQL database exists
- creates the database if missing
- does NOT create any tables
- does NOT run any migrations

There is no Alembic setup. Only a placeholder directory exists at database/migrations_placeholder/.

EXPECTED DATABASE TABLES

Core tables:
- clients
- gst_sessions

GSTR-1 tables:
- gstr1_advance_tax_records
- gstr1_b2b_records
- gstr1_summary_records
- gstr1_b2csa_records
- gstr1_b2cs_records
- gstr1_cdnr_records
- gstr1_doc_issue_records
- gstr1_hsn_records
- gstr1_nil_records
- gstr1_b2cl_records
- gstr1_cdnur_records
- gstr1_exp_records
- gstr1_txp_records

GSTR-2A tables:
- gstr2a_b2b_records
- gstr2a_b2ba_records
- gstr2a_cdn_records
- gstr2a_cdna_records
- gstr2a_document_records
- gstr2a_isd_records
- gstr2a_tds_records

GSTR-2B tables:
- gstr2b_records
- gstr2b_regeneration_status_records

GSTR-3B tables:
- gstr3b_details_records
- gstr3b_auto_liability_records

GSTR-9 tables:
- gstr9_auto_calculated_records
- gstr9_table8a_records
- gstr9_details_records

Ledger tables:
- ledger_cash_itc_balance_records
- ledger_cash_ledger_records
- ledger_itc_ledger_records
- ledger_return_liability_ledger_records

Return status table:
- gst_return_status_records

IMPORTANT ORM PATTERNS

Common mixins:

- PrimaryKeyMixin -> id
- TimestampMixin -> created_at, updated_at
- ClientScopeMixin -> client_id FK clients.id, gstin
- MonthlyPeriodMixin -> year, month
- FinancialYearMixin -> financial_year
- DateRangeMixin -> from_date, to_date
- RawPayloadMixin -> raw_payload JSONB
- JsonRecordMixin -> record_payload JSONB
- TaxAmountsMixin -> taxable_value, tax_rate, igst, cgst, sgst, cess

API LAYER TO SERVICE LAYER MAP

Auth:
- POST /auth/generate-otp -> services.auth.generate_otp
- POST /auth/verify-otp -> services.auth.verify_otp
- POST /auth/refresh -> services.auth.refresh_session
- GET /auth/session/{gstin} -> session_storage.get_session

GSTR-1:
- GET /gstr1/advance-tax/{gstin}/{year}/{month} -> get_gstr1_advance_tax -> gstr1_advance_tax_records
- GET /gstr1/b2b/{gstin}/{year}/{month} -> get_gstr1_b2b -> gstr1_b2b_records
- GET /gstr1/summary/{gstin}/{year}/{month} -> get_gstr1_summary -> gstr1_summary_records
- GET /gstr1/b2csa/{gstin}/{year}/{month} -> get_gstr1_b2csa -> gstr1_b2csa_records
- GET /gstr1/b2cs/{gstin}/{year}/{month} -> get_gstr1_b2cs -> gstr1_b2cs_records
- GET /gstr1/cdnr/{gstin}/{year}/{month} -> get_gstr1_cdnr -> gstr1_cdnr_records
- GET /gstr1/doc-issue/{gstin}/{year}/{month} -> get_gstr1_doc_issue -> gstr1_doc_issue_records
- GET /gstr1/hsn/{gstin}/{year}/{month} -> get_gstr1_hsn -> gstr1_hsn_records
- GET /gstr1/nil/{gstin}/{year}/{month} -> get_gstr1_nil -> gstr1_nil_records
- GET /gstr1/b2cl/{gstin}/{year}/{month} -> get_gstr1_b2cl -> gstr1_b2cl_records
- GET /gstr1/cdnur/{gstin}/{year}/{month} -> get_gstr1_cdnur -> gstr1_cdnur_records
- GET /gstr1/exp/{gstin}/{year}/{month} -> get_gstr1_exp -> gstr1_exp_records
- GET /gstr1/gstr1/{gstin}/{year}/{month}/txp -> get_gstr1_txp -> gstr1_txp_records

GSTR-2A:
- GET /gstr2A/b2b/{gstin}/{year}/{month} -> get_gstr2a_b2b -> gstr2a_b2b_records
- GET /gstr2A/b2ba/{gstin}/{year}/{month} -> get_gstr2a_b2ba -> gstr2a_b2ba_records
- GET /gstr2A/cdn/{gstin}/{year}/{month} -> get_gstr2a_cdn -> gstr2a_cdn_records
- GET /gstr2A/cdna/{gstin}/{year}/{month} -> get_gstr2a_cdna -> gstr2a_cdna_records
- GET /gstr2A/document/{gstin}/{year}/{month} -> get_gstr2a_document -> gstr2a_document_records
- GET /gstr2A/isd/{gstin}/{year}/{month} -> get_gstr2a_isd -> gstr2a_isd_records
- GET /gstr2A/gstr2a/{gstin}/{year}/{month}/tds -> get_gstr2a_tds -> gstr2a_tds_records

GSTR-2B:
- GET /gstr2B/gstr2b/{gstin}/{year}/{month} -> get_gstr2b -> gstr2b_records
- GET /gstr2B/gstr2b/{gstin}/regenerate/status -> get_gstr2b_regeneration_status -> gstr2b_regeneration_status_records

GSTR-3B:
- GET /gstr3B/gstr3b/{gstin}/{year}/{month} -> get_gstr3b_details -> gstr3b_details_records
- GET /gstr3B/gstr3b/{gstin}/{year}/{month}/auto-liability-calc -> get_gstr3b_auto_liability -> gstr3b_auto_liability_records

GSTR-9:
- GET /gstr9/gstr9/{gstin}/auto-calculated -> get_gstr9_auto_calculated -> gstr9_auto_calculated_records
- GET /gstr9/gstr9/{gstin}/table-8a -> get_gstr9_table8a -> gstr9_table8a_records
- GET /gstr9/gstr9/{gstin} -> get_gstr9_details -> gstr9_details_records

Ledgers:
- GET /ledgers/ledgers/{gstin}/{year}/{month}/balance -> get_cash_itc_balance -> ledger_cash_itc_balance_records
- GET /ledgers/ledgers/{gstin}/cash -> get_cash_ledger -> intended ledger_cash_ledger_records
- GET /ledgers/ledgers/{gstin}/itc -> get_itc_ledger -> intended ledger_itc_ledger_records
- GET /ledgers/ledgers/{gstin}/tax/{year}/{month} -> get_return_liability_ledger -> intended ledger_return_liability_ledger_records

Return status:
- GET /return_status/returns/{gstin}/{year}/{month}/status -> get_gst_return_status -> gst_return_status_records

HEALTH:
- GET /health -> simple ok response

SERVICE RESPONSE SHAPES

General pattern:

- Most services return:
  - success
  - request metadata or filter metadata
  - normalized rows or sections
  - raw upstream payload in key `raw`
- Only GSTR-1 advance-tax has an explicit Pydantic response model in OpenAPI.
- Most endpoints effectively return free-form JSON.

Key response shape notes:

- Auth verify/refresh return token/session metadata and upstream response
- GSTR-1 routes usually return `records` or `sections`
- GSTR-2A routes usually return `records`; document returns `b2b`, `b2ba`, `cdn`; TDS returns `tds` plus aggregate totals
- GSTR-2B returns either:
  - regeneration/reference state
  - summary blocks
  - detailed section blocks `b2b`, `b2ba`, `cdnr`, `cdnra`, `isd`
- GSTR-3B returns parsed table-like sections and raw upstream data
- GSTR-9 returns parsed table blocks keyed by table names plus summaries
- Ledger endpoints return balances and/or `transactions`
- Return status returns status metadata and parsed `error_report` sections when present

KNOWN BACKEND ISSUES TO PRESERVE IN CONTEXT

Do not assume the backend is clean. These issues are real and must be considered:

1. No database tables currently exist in PostgreSQL.
2. No migrations exist.
3. DB settings are hardcoded and ignore env-based DATABASE_URL.
4. Sandbox API credentials are hardcoded in config.py.
5. Persistence errors are swallowed, so API success does not guarantee DB success.
6. Async services use blocking requests, which can block the event loop.
7. Session runtime source of truth is JSON, not the database.
8. OpenAPI has no security schemes for protected routes.
9. Some implemented paths contain duplicated segments and mixed casing; use exact current paths for frontend integration.
10. save_ledger_to_db currently inserts transaction rows into all three ledger tables.
11. save_gstr3b_to_db duplicates auto-liability payload into details and auto-liability tables.
12. save_gstr2a_to_db may duplicate or ambiguously persist document endpoint data.
13. frontend/db_proxy.py is unsafe outside local development.

WHAT ANOTHER AI SHOULD DO WITH THIS CONTEXT

- Build a frontend that follows the exact current route contracts, even for odd paths.
- Treat all non-auth GST endpoints as session-dependent.
- Expose session setup first in the UI:
  - generate OTP
  - verify OTP
  - refresh session
  - check session status
- Treat most responses as dynamic JSON, not strict typed schemas.
- If repairing backend integrations, prioritize:
  1. Alembic setup and initial migration
  2. schema creation in PostgreSQL
  3. environment-driven config
  4. replacing blocking requests with async HTTP client
  5. aligning runtime session source of truth
  6. correcting persistence pollution in saver modules

STRUCTURED API SUMMARY FOR FRONTEND GENERATION

POST /auth/generate-otp
- request: OTPGenerate { username, gstin }
- response: dynamic JSON { request_sent, success, message, error_code?, status_cd?, upstream_status_code?, upstream_response? }
- auth: none

POST /auth/verify-otp
- request: OTPVerify { username, gstin, otp }
- response: dynamic JSON { request_sent, success, session_saved, message, error_code?, status_cd?, upstream_status_code?, data?, upstream_response? }
- auth: none

POST /auth/refresh
- request: RefreshRequest { gstin }
- response: dynamic JSON { request_sent, success, session_saved, message, error_code?, status_cd?, upstream_status_code?, data?, upstream_response? }
- auth: active GST session in JSON store

GET /auth/session/{gstin}
- request: path gstin
- response: dynamic JSON { active, username?, token_expiry?, session_expiry?, last_refresh?, message? }
- auth: none

GET /gstr1/advance-tax/{gstin}/{year}/{month}
- request: path gstin/year/month
- response: Gstr1AdvanceTaxResponse { success, request, upstream_status_code, data }
- auth: active GST session

GET /gstr1/b2b/{gstin}/{year}/{month}
- request: path gstin/year/month, query action_required?, from_date?, counterparty_gstin?
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr1/summary/{gstin}/{year}/{month}
- request: path gstin/year/month, query summary_type
- response: dynamic JSON with `sections`
- auth: active GST session

GET /gstr1/b2csa/{gstin}/{year}/{month}
- request: path gstin/year/month
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr1/b2cs/{gstin}/{year}/{month}
- request: path gstin/year/month
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr1/cdnr/{gstin}/{year}/{month}
- request: path gstin/year/month, query action_required?, from?
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr1/doc-issue/{gstin}/{year}/{month}
- request: path gstin/year/month
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr1/hsn/{gstin}/{year}/{month}
- request: path gstin/year/month
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr1/nil/{gstin}/{year}/{month}
- request: path gstin/year/month
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr1/b2cl/{gstin}/{year}/{month}
- request: path gstin/year/month, query state_code?
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr1/cdnur/{gstin}/{year}/{month}
- request: path gstin/year/month
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr1/exp/{gstin}/{year}/{month}
- request: path gstin/year/month
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr1/gstr1/{gstin}/{year}/{month}/txp
- request: path gstin/year/month, query counterparty_gstin?, action_required?, from?
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr2A/b2b/{gstin}/{year}/{month}
- request: path gstin/year/month
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr2A/b2ba/{gstin}/{year}/{month}
- request: path gstin/year/month, query counterparty_gstin?
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr2A/cdn/{gstin}/{year}/{month}
- request: path gstin/year/month, query counterparty_gstin?, from_date?
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr2A/cdna/{gstin}/{year}/{month}
- request: path gstin/year/month, query counterparty_gstin?
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr2A/document/{gstin}/{year}/{month}
- request: path gstin/year/month
- response: dynamic JSON with `b2b`, `b2ba`, `cdn`
- auth: active GST session

GET /gstr2A/isd/{gstin}/{year}/{month}
- request: path gstin/year/month, query counterparty_gstin?
- response: dynamic JSON with `records`
- auth: active GST session

GET /gstr2A/gstr2a/{gstin}/{year}/{month}/tds
- request: path gstin/year/month
- response: dynamic JSON with `tds`, `entry_count`, totals
- auth: active GST session

GET /gstr2B/gstr2b/{gstin}/{year}/{month}
- request: path gstin/year/month, query file_number?
- response: dynamic JSON, shape depends on upstream status and file pagination
- auth: active GST session

GET /gstr2B/gstr2b/{gstin}/regenerate/status
- request: path gstin, query reference_id
- response: dynamic JSON { success, reference_id, regeneration_status, regeneration_status_label, ... }
- auth: active GST session

GET /gstr3B/gstr3b/{gstin}/{year}/{month}
- request: path gstin/year/month
- response: dynamic JSON with parsed sections
- auth: active GST session

GET /gstr3B/gstr3b/{gstin}/{year}/{month}/auto-liability-calc
- request: path gstin/year/month
- response: dynamic JSON with auto liability sections
- auth: active GST session

GET /gstr9/gstr9/{gstin}/auto-calculated
- request: path gstin, query financial_year
- response: dynamic JSON with table summaries
- auth: active GST session

GET /gstr9/gstr9/{gstin}/table-8a
- request: path gstin, query financial_year, file_number
- response: dynamic JSON with `b2b`, `b2ba`, `cdn`, summary
- auth: active GST session

GET /gstr9/gstr9/{gstin}
- request: path gstin, query financial_year
- response: dynamic JSON with parsed GSTR-9 table blocks
- auth: active GST session

GET /ledgers/ledgers/{gstin}/{year}/{month}/balance
- request: path gstin/year/month
- response: dynamic JSON with `cash_balance`, `itc_balance`, `itc_blocked_balance`
- auth: active GST session

GET /ledgers/ledgers/{gstin}/cash
- request: path gstin, query from, to
- response: dynamic JSON with opening_balance, closing_balance, transactions
- auth: active GST session

GET /ledgers/ledgers/{gstin}/itc
- request: path gstin, query from, to
- response: dynamic JSON with opening_balance, closing_balance, transactions
- auth: active GST session

GET /ledgers/ledgers/{gstin}/tax/{year}/{month}
- request: path gstin/year/month, query from, to
- response: dynamic JSON with liability balances and transactions
- auth: active GST session

GET /return_status/returns/{gstin}/{year}/{month}/status
- request: path gstin/year/month, query reference_id
- response: dynamic JSON with processing status and parsed error report sections
- auth: active GST session

GET /health
- request: none
- response: { status: "ok" }
- auth: none
```
