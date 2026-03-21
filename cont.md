SECTION 1 — REPOSITORY ARCHITECTURE
Top-level

main.py — FastAPI application entrypoint; creates app, configures CORS, mounts routers, and runs an async lifespan that calls ensure_database_exists and starts/stops the background session refresh scheduler.
config.py — Global config for the external Sandbox GST API:
BASE_URL, API_KEY, API_SECRET, API_VERSION read from env (with hardcoded defaults).
PLATFORM_TOKEN alias for API_SECRET.
GSTIN and USERNAME sample defaults (e.g. USERNAME="Pgjcoca_1"), mainly used for smoke scripts.
session_storage.py — In-memory + JSON-on-disk session store for taxpayer GST sessions (per GSTIN). No DB dependency here.
smoke_auth_persistence.py — Standalone smoke-test script that:
Forces DATABASE_URL to a local SQLite DB.
Uses TestClient on the FastAPI app, monkeypatches requests.post in services.auth to fake platform responses.
Creates only the clients and gst_sessions tables in the SQLite DB and exercises the auth flow end-to-end, verifying DB persistence.
FastAPI App and Routers

main.py
Creates FastAPI(title="GST API Service", version="2.0.0", lifespan=lifespan).
Adds global CORS via CORSMiddleware(allow_origins=["*"], allow_methods=["*"], ...).
Includes routers:
auth_router.py → auth_router
gst_r1_router.py → gstr1_router
gstr_2A_router.py → gstr2a_router
gstr_2B_router.py → gstr2b_router
gstr_3B_router.py → gstr3b_router
gstr_9_router.py → gstr9_router
ledger_router.py → ledger_router
gst_return_status_router.py → gst_return_status_router
Defines /health health check.
Routers (API layer):
auth_router.py — OTP generation/verification and session refresh for GSTINs; uses auth.py and session_storage.py.
gst_r1_router.py — GSTR-1 endpoints (advance tax, B2B, B2CS, etc.), calling gstr1_service.py.
gstr_2A_router.py — GSTR-2A endpoints, calling gstr_2A_service.py.
gstr_2B_router.py — GSTR-2B endpoints, calling gstr_2B_service.py.
gstr_3B_router.py — GSTR-3B endpoints, calling gstr_3B_service.py.
gstr_9_router.py — GSTR-9 endpoints, calling gstr_9_service.py.
ledger_router.py — GST ledger endpoints, calling ledger_service.py.
gst_return_status_router.py — Return status endpoint, calling gst_return_status_service.py.
Service Layer

Folder: services/
auth.py — Core authentication and OTP/session flows against the platform Sandbox API:
Handles platform-level /authenticate to get a platform access token.
Generates OTP, verifies OTP, and refreshes taxpayer session tokens.
Persists taxpayer session data to in-memory/disk via session_storage.py and to DB via save_auth.py.
gstr1_service.py — All GSTR-1 downstream API integrations:
get_gstr1_advance_tax, get_gstr1_b2b, get_gstr1_summary, get_gstr1_b2csa, get_gstr1_b2cs, get_gstr1_cdnr, get_gstr1_doc_issue, get_gstr1_hsn, get_gstr1_nil, get_gstr1_b2cl, get_gstr1_cdnur, get_gstr1_exp, get_gstr1_txp.
Uses requests (sync) to call Sandbox GST APIs and transforms responses into structured Python dicts or Pydantic models.
Persists interpreted results via save_gstr1.py.
gstr_2A_service.py — GSTR-2A downstream integrations:
get_gstr2a_b2b, get_gstr2a_b2ba, get_gstr2a_cdn, get_gstr2a_cdna, get_gstr2a_document, get_gstr2a_isd, get_gstr2a_tds.
Persists to tables via save_gstr2a.py.
gstr_2B_service.py — GSTR-2B downstream integrations:
get_gstr2b with pagination-aware parsing and get_gstr2b_regeneration_status.
Persists to tables via save_gstr2b.py.
gstr_3B_service.py — GSTR-3B details and auto-liability:
get_gstr3b_details, get_gstr3b_auto_liability.
Persists to models.py via save_gstr3b.py.
gstr_9_service.py — GSTR-9:
get_gstr9_auto_calculated, get_gstr9_table8a, get_gstr9_details.
Persists to models.py via save_gstr9.py.
ledger_service.py — Ledger endpoints:
get_cash_itc_balance, get_cash_ledger, get_itc_ledger, get_return_liability_ledger.
Persists via save_ledger.py.
gst_return_status_service.py — Return status integration and rich error-report parsing; persists to models.py via save_return_status.py.
session_refresh_manager.py — Background scheduler using a thread to periodically call services.auth.refresh_session for all stored sessions via asyncio.run.
services/save_db/ — Persistence helpers:
base_saver.py — Asynchronous DB utilities: AsyncSessionLocal usage, bulk_insert_records, type-coercion utilities, get_or_create_client_id, run_persistence.
save_auth.py — Persists client’s latest session to gst_sessions.
save_gstr1.py — Persists GSTR-1 records to multiple gstr1_* tables.
save_gstr2a.py, save_gstr2b.py, save_gstr3b.py, save_gstr9.py, save_ledger.py, save_return_status.py — Module-specific transformation → bulk insert.
Database / ORM Layer

Config and engine:
config.py — DatabaseSettings with hardcoded default database_url = "postgresql+asyncpg://postgres:root@localhost:5432/gst_platform". Reads DATABASE_ECHO.
database.py — Creates Async SQLAlchemy engine and sessionmaker (engine, AsyncSessionLocal, get_db) and ensure_database_exists which:
Uses asyncpg to check if the target Postgres DB exists; creates it if not (using DATABASE_ADMIN_DB or postgres).
Base + mixins:
base.py — Base DeclarativeBase and mixins:
PrimaryKeyMixin, TimestampMixin, ClientScopeMixin, MonthlyPeriodMixin, FinancialYearMixin, DateRangeMixin, RawPayloadMixin, InvoiceFieldsMixin, NoteFieldsMixin, TaxAmountsMixin, JsonRecordMixin.
Model packages:
client.py — Client table (clients).
session.py — GstSession table (gst_sessions).
models.py — GSTR-1 persistence models (gstr1_* tables).
models.py — GSTR-2A persistence models (gstr2a_* tables).
models.py — GSTR-2B persistence models (gstr2b_* tables).
models.py — GSTR-3B persistence models (gstr3b_* tables).
models.py — GSTR-9 persistence models (gstr9_* tables).
models.py — Return status record.
models.py — Ledger persistence models.
Aggregator:
__init__.py — Re-exports Base, engine, AsyncSessionLocal, get_db, and all ORM models so Alembic or external tooling can import database and see full metadata.
__init__.py — Re-exports Base, engine, AsyncSessionLocal, get_db.
Schemas and Parsers

gstr1.py — Pydantic models for GSTR-1:
Gstr1RequestInfo, Gstr1AdvanceItem, Gstr1AdvanceEntry, Gstr1AdvanceTaxResponse.
gstr1_parser.py — Converts Sandbox response → list of Gstr1AdvanceEntry.
Frontend / Tools

frontend/ and frontend - Copy/ — HTML/JS test harnesses and dashboards for manual API testing (not part of the backend runtime).
smoke_auth.db — SQLite DB used only in smoke_auth_persistence.py.
SECTION 2 — API ENDPOINT MAP
Below is the endpoint registry with router, method, path, service function, schemas (where applicable), auth requirement, and DB usage. All endpoints are mounted under the root FastAPI app.

Auth Router — auth_router.py
Generate OTP

Method/Path: POST /auth/generate-otp
Request body: OTPGenerate { username: str, gstin: str }
Service: services.auth.generate_otp(username, gstin)
Response: JSON dict with:
request_sent, success, message, error_code, status_cd, upstream_status_code, upstream_response.
Auth requirement:
Uses platform-level auth only (API key/secret), no taxpayer session yet.
DB usage:
No DB writes (only uses platform token and in-memory OTP context).
Verify OTP

Method/Path: POST /auth/verify-otp
Request body: OTPVerify { username: str, gstin: str, otp: str }
Service: services.auth.verify_otp(username, gstin, otp)
Response: JSON dict with:
request_sent, success, session_saved, message, error_code, status_cd, upstream_status_code, data, upstream_response.
Auth requirement:
Uses platform token + OTP auth context (cached authorization token).
DB usage:
In-memory/disk: session_storage.save_session(...) persists access/refresh token to the sessions directory.
DB: save_auth_session_to_db(...) writes/updates a GstSession row (table gst_sessions) for that GSTIN/client.
Refresh Session

Method/Path: POST /auth/refresh
Request body: RefreshRequest { gstin: str }
Service: services.auth.refresh_session(gstin)
Response: JSON dict similar to verify-otp format but focused on refresh operation.
Auth requirement:
Requires an existing taxpayer session in session_storage (uses taxpayer access_token as Authorization).
DB usage:
On success, updates the existing GstSession record via save_auth_session_to_db, mirroring the refreshed tokens/expiry.
Session Status

Method/Path: GET /auth/session/{gstin}
Service: Directly uses session_storage.get_session(gstin)
Response: JSON dict:
If no session: { "active": False, "message": "No session found for this GSTIN." }
If session: {"active": bool(access_token), "username", "token_expiry", "session_expiry", "last_refresh"}
Auth requirement:
None (public diagnostic for sessions).
DB usage:
None (purely uses in-memory/on-disk session storage).
GSTR-1 Router — gst_r1_router.py
All GSTR-1 endpoints require a valid GST taxpayer session (i.e., OTP verified beforehand). They all use session_storage.get_session indirectly through gstr1_service.py. They all hit external GST APIs and then persist into Postgres tables via save_gstr1.py.

Advance Tax (AT)

Method/Path: GET /gstr1/advance-tax/{gstin}/{year}/{month}
Service: get_gstr1_advance_tax(gstin, year, month)
Request schema:
Path: gstin: str, year: str, month: str.
Response schema:
Gstr1AdvanceTaxResponse Pydantic model (see gstr1.py):
success, request: Gstr1RequestInfo, upstream_status_code, data: Dict[str, Any] with "parsed" and "raw".
Auth requirement:
Must have a valid taxpayer session in session_storage (uses access_token as Authorization).
DB usage:
Persists parsed entries to gstr1_advance_tax_records via save_gstr1_to_db.
B2B Invoices

Method/Path: GET /gstr1/b2b/{gstin}/{year}/{month}
Query params: action_required: str|None, from_date: str|None, counterparty_gstin: str|None.
Service: get_gstr1_b2b(gstin, year, month, action_required, from_date, counterparty_gstin)
Response: Dict:
success, request, summary, invoices[], raw.
Auth requirement: taxpayer access_token.
DB usage:
Persists invoices to gstr1_b2b_records.
Summary

Method/Path: GET /gstr1/summary/{gstin}/{year}/{month}
Query: summary_type="short"|"long" (default "short").
Service: get_gstr1_summary(gstin, year, month, summary_type)
Response: Dict with success, gstin, ret_period, sections[], raw.
DB usage:
Persists per-section summary rows into gstr1_summary_records.
B2CSA

Method/Path: GET /gstr1/b2csa/{gstin}/{year}/{month}
Service: get_gstr1_b2csa(gstin, year, month)
Response: Dict: success, request, records[], raw.
DB usage:
Persists to gstr1_b2csa_records.
B2CS

Method/Path: GET /gstr1/b2cs/{gstin}/{year}/{month}
Service: get_gstr1_b2cs(gstin, year, month)
DB table: gstr1_b2cs_records.
CDNR

Method/Path: GET /gstr1/cdnr/{gstin}/{year}/{month}
Query: action_required: str|None, from_date: str|None.
Service: get_gstr1_cdnr(...)
DB table: gstr1_cdnr_records.
Document Issue

Method/Path: GET /gstr1/doc-issue/{gstin}/{year}/{month}
Service: get_gstr1_doc_issue(...)
DB table: gstr1_doc_issue_records.
HSN Summary

Method/Path: GET /gstr1/hsn/{gstin}/{year}/{month}
Service: get_gstr1_hsn(...)
DB table: gstr1_hsn_records.
Nil/Exempt/Non-GST

Method/Path: GET /gstr1/nil/{gstin}/{year}/{month}
Service: get_gstr1_nil(...)
DB table: gstr1_nil_records.
B2CL

Method/Path: GET /gstr1/b2cl/{gstin}/{year}/{month}
Query: state_code: str | None
Service: get_gstr1_b2cl(...)
DB table: gstr1_b2cl_records.
CDNUR

Method/Path: GET /gstr1/cdnur/{gstin}/{year}/{month}
Service: get_gstr1_cdnur(...)
DB table: gstr1_cdnur_records.
EXP (Exports)

Method/Path: GET /gstr1/exp/{gstin}/{year}/{month}
Service: get_gstr1_exp(...)
DB table: gstr1_exp_records.
TXP (Advance Tax Paid)

Method/Path (note prefix duplication): GET /gstr1/gstr1/{gstin}/{year}/{month}/txp
Full URL is /gstr1/gstr1/{gstin}/{year}/{month}/txp due to router prefix.
Query: counterparty_gstin, action_required, from (from_date).
Service: get_gstr1_txp(gstin, year, month, counterparty_gstin, action_required, from_date)
DB table: gstr1_txp_records.
GSTR-2A Router — gstr_2A_router.py
Endpoints all require taxpayer session and persist via save_gstr2a.py.

GET /gstr2A/b2b/{gstin}/{year}/{month} → get_gstr2a_b2b → gstr2a_b2b_records.
GET /gstr2A/b2ba/{gstin}/{year}/{month}?counterparty_gstin → get_gstr2a_b2ba → gstr2a_b2ba_records.
GET /gstr2A/cdn/{gstin}/{year}/{month}?counterparty_gstin&from → get_gstr2a_cdn → gstr2a_cdn_records.
GET /gstr2A/cdna/{gstin}/{year}/{month}?counterparty_gstin → get_gstr2a_cdna → gstr2a_cdna_records.
GET /gstr2A/document/{gstin}/{year}/{month} → get_gstr2a_document → multiple GSTR2A tables (b2b/b2ba/cdn & document records).
GET /gstr2A/isd/{gstin}/{year}/{month}?counterparty_gstin → get_gstr2a_isd → gstr2a_isd_records.
GET /gstr2A/gstr2a/{gstin}/{year}/{month}/tds → get_gstr2a_tds → gstr2a_tds_records.
GSTR-2B Router — gstr_2B_router.py
GET /gstr2B/gstr2b/{gstin}/{year}/{month}?file_number
→ get_gstr2b(gstin, year, month, file_number)
→ Persists summary or document rows to gstr2b_records.
GET /gstr2B/gstr2b/{gstin}/regenerate/status?reference_id
→ get_gstr2b_regeneration_status(gstin, reference_id)
→ Persists to gstr2b_regeneration_status_records.
GSTR-3B Router — gstr_3B_router.py
GET /gstr3B/gstr3b/{gstin}/{year}/{month}
→ get_gstr3b_details(gstin, year, month)
→ Persists structured sections to gstr3b_details_records.
GET /gstr3B/gstr3b/{gstin}/{year}/{month}/auto-liability-calc
→ get_gstr3b_auto_liability(gstin, year, month)
→ Persists sections to gstr3b_auto_liability_records.
GSTR-9 Router — gstr_9_router.py
GET /gstr9/gstr9/{gstin}/auto-calculated?financial_year
→ get_gstr9_auto_calculated(gstin, financial_year)
→ Persists to gstr9_auto_calculated_records.
GET /gstr9/gstr9/{gstin}/table-8a?financial_year&file_number
→ get_gstr9_table8a(gstin, financial_year, file_number)
→ Persists to gstr9_table8a_records.
GET /gstr9/gstr9/{gstin}?financial_year
→ get_gstr9_details(gstin, financial_year)
→ Persists to gstr9_details_records.
Ledger Router — ledger_router.py
GET /ledgers/ledgers/{gstin}/{year}/{month}/balance
→ get_cash_itc_balance(gstin, year, month)
→ Persists to ledger_cash_itc_balance_records.
GET /ledgers/ledgers/{gstin}/cash?from&to
→ get_cash_ledger(gstin, from_date, to_date)
→ Persists to ledger_cash_ledger_records.
GET /ledgers/ledgers/{gstin}/itc?from&to
→ get_itc_ledger(gstin, from_date, to_date)
→ Persists to ledger_itc_ledger_records.
GET /ledgers/ledgers/{gstin}/tax/{year}/{month}?from&to
→ get_return_liability_ledger(gstin, year, month, from_date, to_date)
→ Persists to ledger_return_liability_ledger_records.
GST Return Status Router — gst_return_status_router.py
GET /return_status/returns/{gstin}/{year}/{month}/status?reference_id
→ get_gst_return_status(gstin, year, month, reference_id)
→ Persists to gst_return_status_records.
SECTION 3 — SERVICE LAYER MAP
For each major service module:

Auth Service — auth.py

_authenticate_platform(force_refresh=False) — Obtains and caches platform access token.
_post_with_platform_auth(...) — Wrapper for POST with automatic re-auth on auth errors.
generate_otp(username, gstin) — Initiates OTP to GST system.
Models accessed: None.
DB usage: None (only auth session saved on verify).
verify_otp(username, gstin, otp) — Verifies OTP and persists taxpayer session.
Uses session_storage.save_session + save_auth_session_to_db.
Models: Client, GstSession.
refresh_session(gstin) — Extends GST session by 6 hours without OTP.
Uses stored taxpayer access_token and refresh_token.
Updates GstSession via save_auth_session_to_db.
Session Scheduler — session_refresh_manager.py

start_scheduler() / stop_scheduler() — Manage a daemon thread that periodically:
Iterates over session_storage.get_all_sessions(), calls refresh_session(gstin) via asyncio.run.
manual_refresh(gstin) — On-demand refresh for a GSTIN.
GSTR-1 Service — gstr1_service.py

All functions:

Use session_storage.get_session(gstin); if missing, return success=False with user-friendly error.
Use requests.get with Authorization = taxpayer token plus x-api-key, x-api-version.
Parse nested GST payload into structured Python dicts.
Call save_gstr1_to_db(...) to persist.
Key functions and models:

get_gstr1_advance_tax → Gstr1AdvanceTaxRecord via parser.
get_gstr1_b2b → Gstr1B2BRecord.
get_gstr1_summary → Gstr1SummaryRecord.
get_gstr1_b2csa → Gstr1B2CSARecord.
get_gstr1_b2cs → Gstr1B2CSRecord.
get_gstr1_cdnr → Gstr1CDNRRecord.
get_gstr1_doc_issue → Gstr1DocIssueRecord.
get_gstr1_hsn → Gstr1HSNRecord.
get_gstr1_nil → Gstr1NilRecord.
get_gstr1_b2cl → Gstr1B2CLRecord.
get_gstr1_cdnur → Gstr1CDNURRecord.
get_gstr1_exp → Gstr1EXPRecord.
get_gstr1_txp → Gstr1TXPRecord.
GSTR-2A Service — gstr_2A_service.py

get_gstr2a_b2b → Gstr2AB2BRecord.
get_gstr2a_b2ba → Gstr2AB2BARecord.
get_gstr2a_cdn → Gstr2ACDNRecord.
get_gstr2a_cdna → Gstr2ACDNARecord.
get_gstr2a_document → Gstr2ADocumentRecord plus Gstr2AB2BRecord/Gstr2AB2BARecord/Gstr2ACDNRecord.
get_gstr2a_isd → Gstr2AISDRecord.
get_gstr2a_tds → Gstr2ATDSRecord.
GSTR-2B Service — gstr_2B_service.py

get_gstr2b:
Uses rich parsing helpers (_parse_b2b_section, _parse_cdnr_section, _parse_isd_section, _parse_cpsumm, _parse_itcsumm).
Handles:
status_cd="0" → error.
status_cd="3" → pagination (returns file_count).
status_cd="1" → summary or full docdata.
Persists:
Summary or docdata records into Gstr2BRecord via save_gstr2b_to_db.
get_gstr2b_regeneration_status:
Persists into Gstr2BRegenerationStatusRecord.
GSTR-3B Service — gstr_3B_service.py

get_gstr3b_details:
Parses: supply details, inter-state supplies, eligible ITC, inward supplies, interest & late fee, tax payment.
Persists each major section as a JSON blob row in Gstr3BDetailsRecord.
get_gstr3b_auto_liability:
Parses liabitc, sup_details, inter_sup.
Persists sections in Gstr3BAutoLiabilityRecord.
GSTR-9 Service — gstr_9_service.py

get_gstr9_auto_calculated:
Parses tables 4,5,6,8,9 from auto-calculated GST data.
Persists to Gstr9AutoCalculatedRecord.
get_gstr9_table8a:
Parses supplier group entries into B2B/B2BA/CDN document sets.
Persists to Gstr9Table8ARecord.
get_gstr9_details:
Parses multiple tables (4–10, 17) from manually filed return.
Persists to Gstr9DetailsRecord.
Ledger Service — ledger_service.py

get_cash_itc_balance:
Reads cash_bal, itc_bal, itc_blck_bal; flattens into components; persisted as LedgerCashItcBalanceRecord.
get_cash_ledger:
Opening/closing balances and transaction entries; persisted as LedgerCashLedgerRecord.
get_itc_ledger:
ITC ledger transactions; persisted as LedgerItcLedgerRecord.
get_return_liability_ledger:
Tax liability ledger; persisted as LedgerReturnLiabilityLedgerRecord.
Return Status Service — gst_return_status_service.py

get_gst_return_status(gstin, year, month, reference_id):
Parses outer status_cd and inner status_cd (P, PE, ER, REC).
Parses complex error_report structure into strongly-typed sections (b2b, b2cl, b2cs, cdnr, cdnur, exp, at, txpd, hsn, nil, doc_issue, table17).
Persists a single GstReturnStatusRecord row containing status, form type, and error_report JSON.
SECTION 4 — DATABASE MODELS
All models inherit from Base in base.py. Below is a summary by table.

Core / Auth

Client (client.py)

Table: clients
Columns:
id (PK, int, autoincrement)
gstin (str, 15, unique, indexed)
legal_name (str, optional)
Relationships:
sessions → GstSession (one-to-many).
GstSession (session.py)

Table: gst_sessions
Columns:
id (PK)
client_id (FK → clients.id, indexed, ondelete CASCADE)
access_token (Text)
refresh_token (Text, nullable)
username (str, nullable)
token_expiry, session_expiry, last_refresh (timezone-aware DateTime, nullable)
Timestamps from TimestampMixin.
GSTR-1 Tables — models.py

All extend _Gstr1Base (PK, client_id, gstin, year, month, raw_payload JSONB, timestamps).

Gstr1AdvanceTaxRecord → gstr1_advance_tax_records
Gstr1B2BRecord → gstr1_b2b_records
Gstr1SummaryRecord → gstr1_summary_records
Gstr1B2CSARecord → gstr1_b2csa_records
Gstr1B2CSRecord → gstr1_b2cs_records
Gstr1CDNRRecord → gstr1_cdnr_records
Gstr1DocIssueRecord → gstr1_doc_issue_records
Gstr1HSNRecord → gstr1_hsn_records
Gstr1NilRecord → gstr1_nil_records
Gstr1B2CLRecord → gstr1_b2cl_records
Gstr1CDNURRecord → gstr1_cdnur_records
Gstr1EXPRecord → gstr1_exp_records
Gstr1TXPRecord → gstr1_txp_records
These tables include rich fields for GSTIN, supply type, invoice/note information, tax amounts (taxable_value, igst, cgst, sgst, cess, tax_rate), and sometimes item_number, flag, checksum.

GSTR-2A Tables — models.py

All extend _Gstr2ABase (client/gstin/month/year/raw).

Gstr2AB2BRecord → gstr2a_b2b_records
Gstr2AB2BARecord → gstr2a_b2ba_records
Gstr2ACDNRecord → gstr2a_cdn_records
Gstr2ACDNARecord → gstr2a_cdna_records
Gstr2ADocumentRecord → gstr2a_document_records
Gstr2AISDRecord → gstr2a_isd_records
Gstr2ATDSRecord → gstr2a_tds_records
GSTR-2B Tables — models.py

_Gstr2BBase — same mixins as above.
Gstr2BRecord → gstr2b_records:
Contains both normalized and JSON record payloads, plus metadata (status_cd, response_type, file_count, file_number, section, etc.).
Gstr2BRegenerationStatusRecord → gstr2b_regeneration_status_records:
Reference ID and regeneration status/labels.
GSTR-3B Tables — models.py

_Gstr3BBase — client/gstin/month/year/raw.
Gstr3BDetailsRecord → gstr3b_details_records
Gstr3BAutoLiabilityRecord → gstr3b_auto_liability_records
Each record stores a section key and record_payload JSON summarizing one logical subsection of GSTR-3B.

GSTR-9 Tables — models.py

_Gstr9Base — client/gstin/financial_year/raw.
_Gstr9LineMixin — standardized line-level fields:
table_code, section_code, section_label, supplier_gstin, filing_date, return_period, invoice/note/HSN fields, tax amounts, payment splits.
Gstr9AutoCalculatedRecord → gstr9_auto_calculated_records
Gstr9Table8ARecord → gstr9_table8a_records
Gstr9DetailsRecord → gstr9_details_records
Return Status Table — models.py

GstReturnStatusRecord → gst_return_status_records
Fields: reference_id, status_cd, form_type, form_type_label, action, processing_status, processing_status_label, has_errors, error_code, error_message, error_report JSONB, plus client/gstin/year/month/raw.
Ledger Tables — models.py

_LedgerBase — client/gstin/raw/timestamps.
LedgerCashItcBalanceRecord → ledger_cash_itc_balance_records (snapshot-type per tax head and component).
LedgerCashLedgerRecord → ledger_cash_ledger_records (date range, entry_type, transaction metadata).
LedgerItcLedgerRecord → ledger_itc_ledger_records.
LedgerReturnLiabilityLedgerRecord → ledger_return_liability_ledger_records.
SECTION 5 — DATABASE SCHEMA (AGGREGATED)
Tables by logical area

Core:
clients, gst_sessions.
GSTR-1:
gstr1_advance_tax_records, gstr1_b2b_records, gstr1_summary_records, gstr1_b2csa_records, gstr1_b2cs_records, gstr1_cdnr_records, gstr1_doc_issue_records, gstr1_hsn_records, gstr1_nil_records, gstr1_b2cl_records, gstr1_cdnur_records, gstr1_exp_records, gstr1_txp_records.
GSTR-2A:
gstr2a_b2b_records, gstr2a_b2ba_records, gstr2a_cdn_records, gstr2a_cdna_records, gstr2a_document_records, gstr2a_isd_records, gstr2a_tds_records.
GSTR-2B:
gstr2b_records, gstr2b_regeneration_status_records.
GSTR-3B:
gstr3b_details_records, gstr3b_auto_liability_records.
GSTR-9:
gstr9_auto_calculated_records, gstr9_table8a_records, gstr9_details_records.
Return Status:
gst_return_status_records.
Ledgers:
ledger_cash_itc_balance_records, ledger_cash_ledger_records, ledger_itc_ledger_records, ledger_return_liability_ledger_records.
Indexing / keys

All tables share id PK and created_at/updated_at.
Client scope:
client_id + gstin present and indexed via mixins.
Period fields:
year, month, financial_year indexed.
Date range:
from_date, to_date indexed where present.
Many invoice/note date fields also indexed (via index=True).
SECTION 6 — DATABASE CONNECTION DETAILS
Configuration

Primary settings: config.py
Default database_url = "postgresql+asyncpg://postgres:root@localhost:5432/gst_platform".
echo_sql toggled by DATABASE_ECHO env var.
Engine & sessions: database.py
engine: AsyncEngine = create_async_engine(settings.database_url, echo=settings.echo_sql, pool_pre_ping=True).
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False, autocommit=False).
get_db() yields AsyncSession instances for DI (not currently used in routers).
Database auto-create:
ensure_database_exists():
If URL is Postgres, uses asyncpg.connect to target DB.
If DB missing, connects to admin DB (default postgres or DATABASE_ADMIN_DB) and issues CREATE DATABASE "{db_name}".
Called once in lifespan of main.py.
Usage Patterns

Request-time DB usage:
No routers call Depends(get_db); no classic CRUD endpoints.
Instead, all DB interaction happens in background, inside service functions via the persistence helpers.
Persistence pipeline:
run_persistence(work) in base_saver.py:
async with AsyncSessionLocal() as session: await work(session); await session.commit().
Catches SQLAlchemyError and some OS/connectivity errors; on connectivity failure logs a warning and skips persistence without breaking API responses.
Smoke test DB:
smoke_auth_persistence.py sets DATABASE_URL to SQLite and explicitly creates only clients and gst_sessions within that SQLite DB for test purposes (not production).
SECTION 7 — DETECTED INFRASTRUCTURE ISSUES
No Migration System in Place

README.md explicitly states migrations are not set up and suggests Alembic.
There is no alembic/, migrations/, or versions/ directory in the repo, and no Base.metadata.create_all call against Postgres.
Consequence:
In the real Postgres DB (gst_platform), none of the ORM tables will exist until migrations are run or tables are created manually.
Persistence helpers (save_gstr1_to_db, etc.) will likely encounter UndefinedTable errors (e.g., relation "clients" does not exist) on first write.
These errors are caught and downgraded to warnings in run_persistence, so endpoints continue to respond but no data is stored in Postgres.
Dual DB Behaviors (SQLite vs Postgres)

smoke_auth_persistence.py uses SQLite (sqlite+aiosqlite:///./smoke_auth.db) and explicitly creates Client and GstSession tables via run_sync(table.create(checkfirst=True)).
This makes the smoke test pass even though the main Postgres DB has no migrations.
This discrepancy can hide missing-table issues until production deployment.
Blocking HTTP Calls in Async Services

All downstream API calls (requests.get, requests.post) are made from async def service functions without using an async HTTP client.
This blocks the event loop on network I/O; for high concurrency this will reduce throughput and may cause timeouts.
No Use of get_db Dependency

Although get_db exists and exports an AsyncSession dependency, no FastAPI routes use it.
All DB operations are write-only, performed inside background persistence helpers. There are no read endpoints backed by the DB.
Hardcoded Default API Credentials

config.py falls back to live-looking keys/secrets as defaults when env vars are missing.
For security/ops, these should be env-only, but this is a configuration concern rather than a functional bug.
Inconsistent Route Paths

Some routes have duplicate segments due to prefix + path naming, e.g.:
router = APIRouter(prefix="/gstr1", ...) with path "/gstr1/{gstin}/{year}/{month}/txp" → /gstr1/gstr1/....
router = APIRouter(prefix="/ledgers", ...) with paths beginning with /ledgers/... → /ledgers/ledgers/....
Behavior is correct but confusing for API consumers.
Database Session Life-cycle

run_persistence opens and closes a new AsyncSession for each persistence task.
There is no pooling of per-request sessions or transactions combining multiple writes; this can be expensive for very high volume.
However, this pattern is simple and safe (each save is isolated).
SECTION 8 — MIGRATION STATUS
Current State

No Alembic configuration in the repo.
No migration scripts.
Base.metadata is not used to create tables in Postgres at startup.
Only the SQLite smoke test explicitly creates tables, and only for clients and gst_sessions.
Required Migrations

All tables defined under models and services must be included in the initial migration:

Core:
clients, gst_sessions.
GSTR-1:
gstr1_advance_tax_records, gstr1_b2b_records, gstr1_summary_records, gstr1_b2csa_records, gstr1_b2cs_records, gstr1_cdnr_records, gstr1_doc_issue_records, gstr1_hsn_records, gstr1_nil_records, gstr1_b2cl_records, gstr1_cdnur_records, gstr1_exp_records, gstr1_txp_records.
GSTR-2A:
gstr2a_b2b_records, gstr2a_b2ba_records, gstr2a_cdn_records, gstr2a_cdna_records, gstr2a_document_records, gstr2a_isd_records, gstr2a_tds_records.
GSTR-2B:
gstr2b_records, gstr2b_regeneration_status_records.
GSTR-3B:
gstr3b_details_records, gstr3b_auto_liability_records.
GSTR-9:
gstr9_auto_calculated_records, gstr9_table8a_records, gstr9_details_records.
Return Status:
gst_return_status_records.
Ledgers:
ledger_cash_itc_balance_records, ledger_cash_ledger_records, ledger_itc_ledger_records, ledger_return_liability_ledger_records.
Recommended Fix (Backend-only, for Lovable’s context)

Initialize Alembic with target_metadata = database.Base.metadata (import Base from __init__.py).
Generate initial migration reflecting all current tables.
Apply migrations to the Postgres database specified by DATABASE_URL or config.py.
SECTION 9 — FULL SYSTEM CONTEXT PROMPT FOR AI (FOR LOVABLE)
You are integrating with an existing FastAPI backend that exposes GST-related read APIs over the official Sandbox API and persists normalized data into a Postgres database through SQLAlchemy ORM.

9.1 High-Level Architecture
Framework: FastAPI with async lifespan.

Entry point: main.py

Creates the FastAPI app, configures CORS.
On startup, calls ensure_database_exists() to guarantee the Postgres database itself exists (but does not create tables).
Mounts multiple routers for authentication, GSTR* returns, ledgers, and return status.
External Dependencies:

A third-party GST Sandbox API hosted at BASE_URL (default "https://api.sandbox.co.in") with API keys/secrets configured in config.py.
A Postgres database (postgresql+asyncpg://postgres:root@localhost:5432/gst_platform by default).
Authentication Strategy:

Platform-level access token (via /authenticate with x-api-key, x-api-secret, x-api-version).
Taxpayer-level session token (via OTP flows against GST endpoints).
Taxpayer access tokens are stored in:
A JSON file in sessions/{GSTIN}_session.json and an in-memory dict via session_storage.py.
A gst_sessions table linked to a clients table in the Postgres DB for historical tracking.
A background scheduler regularly refreshes taxpayer sessions using refresh_session(gstin).
Persistence Strategy:

The app itself does not serve CRUD endpoints over its own DB.
Instead, every downstream GST call (GSTR-1/2A/2B/3B/9, ledgers, return status) parses the Sandbox response and then hands it to a save_* module which writes normalized rows into the DB.
Each save_* module opens a new AsyncSession from AsyncSessionLocal, bulk-inserts ORM models, and commits.
Frontend Role (Lovable):

The frontend should call this backend’s REST APIs.
The backend will reach out to the GST Sandbox, parse responses, and (if DB is properly migrated) store the data in Postgres for later analytics, dashboards, and exports.
9.2 API Layer Summary (for Routing & Frontend)
Global notes:

All GSTR* and ledger endpoints assume you have first:
Called /auth/generate-otp with gstin and username.
Called /auth/verify-otp with the OTP.
Without a valid session in session_storage.py, these endpoints return success=False with a message like "GST session not found. Verify OTP first.".
Auth Endpoints (Session Bootstrap):

POST /auth/generate-otp
Request: JSON { "username": string, "gstin": string }
Response: JSON dictionary including success, message, status_cd, error_code.
Auth: platform API key/secret only.
POST /auth/verify-otp
Request: JSON { "username": string, "gstin": string, "otp": string }
Response: JSON; when success=true, taxpayer session is created and saved both in-memory/on-disk and in DB (gst_sessions).
POST /auth/refresh
Request: JSON { "gstin": string }
Response: JSON; when success=true, session expiry is extended.
GET /auth/session/{gstin}
Response: JSON { active: bool, username?, token_expiry?, session_expiry?, last_refresh? }.
GSTR-1 Endpoints (All under /gstr1)

GET /gstr1/advance-tax/{gstin}/{year}/{month}
Response model: Gstr1AdvanceTaxResponse.
Returns a structured object with request info and data containing parsed advance-tax entries.
GET /gstr1/b2b/{gstin}/{year}/{month}?action_required&from_date&counterparty_gstin
Returns a JSON dict with summary and line-level invoices from the B2B section.
GET /gstr1/summary/{gstin}/{year}/{month}?summary_type=short|long
Returns summarized totals per section (e.g., B2B, B2CS, etc.).
GET /gstr1/b2csa, /b2cs, /cdnr, /doc-issue, /hsn, /nil, /b2cl, /cdnur, /exp, /gstr1/gstr1/{gstin}/{year}/{month}/txp
All return JSON structures representing their respective GSTR-1 sections.
GSTR-2A Endpoints (under /gstr2A)

B2B, B2BA, CDN, CDNA, document, ISD, TDS endpoints.
All return JSON arrays/dicts; each endpoint corresponds to one or more underlying DB tables for analytics.
GSTR-2B Endpoints (under /gstr2B)

GET /gstr2B/gstr2b/{gstin}/{year}/{month}?file_number
First call without file_number may indicate pagination (status_cd=3 with file_count).
Subsequent calls with file_number=1..file_count return document pages.
GET /gstr2B/gstr2b/{gstin}/regenerate/status?reference_id
Returns regeneration status.
GSTR-3B Endpoints (under /gstr3B)

GET /gstr3B/gstr3b/{gstin}/{year}/{month} — returns a full breakdown of Table 3.x/4/5/6 etc.
GET /gstr3B/gstr3b/{gstin}/{year}/{month}/auto-liability-calc — returns auto-calculated liability and ITC suggestions.
GSTR-9 Endpoints (under /gstr9)

GET /gstr9/gstr9/{gstin}/auto-calculated?financial_year
GET /gstr9/gstr9/{gstin}/table-8a?financial_year&file_number
GET /gstr9/gstr9/{gstin}?financial_year
Ledger Endpoints (under /ledgers)

GET /ledgers/ledgers/{gstin}/{year}/{month}/balance
GET /ledgers/ledgers/{gstin}/cash?from&to
GET /ledgers/ledgers/{gstin}/itc?from&to
GET /ledgers/ledgers/{gstin}/tax/{year}/{month}?from&to
Return Status Endpoint

GET /return_status/returns/{gstin}/{year}/{month}/status?reference_id
Returns detailed processing status for form_typ in {"R1", "R3B", "R9"} and, when errors occur, a structured error_report by section.
9.3 Service → Model → Table Mappings
For frontend and integration understanding, each API call follows this pattern:

Route → Service → DB Table(s)
Examples:

/gstr1/advance-tax/... → get_gstr1_advance_tax → Gstr1AdvanceTaxRecord → gstr1_advance_tax_records.
/gstr1/b2b/... → get_gstr1_b2b → Gstr1B2BRecord → gstr1_b2b_records.
/gstr2A/b2b/... → get_gstr2a_b2b → Gstr2AB2BRecord → gstr2a_b2b_records.
/gstr2B/gstr2b/... → get_gstr2b → Gstr2BRecord → gstr2b_records.
/gstr3B/gstr3b/... → get_gstr3b_details → Gstr3BDetailsRecord → gstr3b_details_records.
/gstr9/gstr9/...auto-calculated → get_gstr9_auto_calculated → Gstr9AutoCalculatedRecord → gstr9_auto_calculated_records.
/ledgers/ledgers/{gstin}/{year}/{month}/balance → get_cash_itc_balance → LedgerCashItcBalanceRecord → ledger_cash_itc_balance_records.
/return_status/returns/.../status → get_gst_return_status → GstReturnStatusRecord → gst_return_status_records.
9.4 Authentication and Session Model
Platform Authentication

When any GST call is made, the service obtains a platform-level access token via /authenticate and caches it in process (with expiry from JWT payload).
Headers include Authorization: <platform_token>, x-api-key, x-api-version, x-source: primary.
Taxpayer Session Authentication

OTP flows generate a taxpayer-specific access_token and refresh_token.
session_storage holds them per GSTIN and ensures expiry handling.
All GST taxpayer calls use Authorization: <taxpayer_access_token> plus API key/version headers.
Background Refresh

session_refresh_manager starts at app startup and periodically runs refresh_session on active sessions.
9.5 Infrastructure Fixes Needed (for a Robust Deployment)
When Lovable builds UI and helps adjust the backend wiring, these infra issues should be addressed (without changing endpoint semantics):

Enable and Run Alembic Migrations

Set up Alembic with target_metadata = database.Base.metadata.
Generate an initial migration for every ORM model listed above.
Apply migrations to the Postgres DB before relying on any persistence behavior.
Without this, DB writes will silently fail, and analytics views built on top of DB tables will be empty.
Align DATABASE_URL Configuration

Replace hardcoded default in config.py with environment-driven config (e.g. DATABASE_URL env var).
Ensure that smoke_auth_persistence.py does not conflict with production database configuration (or isolate it as a dev-only tool).
(Optional) Introduce Async HTTP Client

Replace blocking requests in async endpoints with an async HTTP client (httpx.AsyncClient).
This is a performance fix, not a functional one, and can be done without changing endpoint signatures.
(Optional) Normalize Route Paths

Keep existing routes for backward compatibility, but optionally add new, cleaner paths (e.g., /gstr1/txp/{gstin}/{year}/{month} as an alias to the current duplicated path) and document them.
(Optional) DB-Backed Read Endpoints

Currently all data is served directly from the GST Sandbox every time.
You may add separate endpoints (e.g., /db/gstr1/...) that read from the persisted tables via Depends(get_db), enabling dashboards that query historical data without hitting the GST APIs every time.
This can coexist with the existing API surface.
9.6 Structured API Summary for Frontend Generation
For each endpoint, the frontend should know:

Endpoint: full path relative to API root.
Method: HTTP verb.
Request schema: JSON body and/or path/query parameters.
Response schema: either a Pydantic model (where defined) or “JSON object with keys X”.
Authentication: “Requires prior OTP verification for GSTIN” or “No auth”.
You can derive this from Section 2 but here is a concise template for Lovable:

/auth/generate-otp (POST)

Body: { username: string, gstin: string }
Response: { success: boolean, message: string, status_cd?: string, error_code?: string, ... }
Auth: None (uses platform key/secret only).
/auth/verify-otp (POST)

Body: { username: string, gstin: string, otp: string }
Response: { success: boolean, session_saved: boolean, message: string, data?: object, ... }
Auth: None (uses platform token + OTP context; this establishes taxpayer session).
/auth/refresh (POST)

Body: { gstin: string }
Response: { success: boolean, message: string, ... }
Auth: Requires existing taxpayer session.
/auth/session/{gstin} (GET)

Response: { active: boolean, username?: string, token_expiry?: any, session_expiry?: any, last_refresh?: any }
Auth: None.
All /gstr1/*, /gstr2A/*, /gstr2B/*, /gstr3B/*, /gstr9/*, /ledgers/*, /return_status/* endpoints

Path params: always include gstin and often year, month or financial_year.
Query params: summary_type, action_required, from (dates), counterparty_gstin, file_number, reference_id, etc. as documented in Section 2.
Response: JSON objects consistent with service return values.
Auth: Always requires a valid taxpayer session (OTP verified) except /return_status/*, which still requires taxpayer session for GST API access.
This backend is ready for a frontend that:

Guides the user through OTP-based session creation for a GSTIN.
Calls the various /gstr* and /ledgers endpoints to fetch views of their GST data.
Optionally, later consumes DB-backed analytic endpoints built on top of the persisted Postgres tables once migrations are in place.
This entire description, including the file references and route→service→model mapping, should give you (Lovable) enough context to generate a comprehensive dashboard UI and to propose safe, backwards-compatible backend fixes focused on infrastructure (migrations, configuration, async I/O) without altering business logic or route semantics.