# GST Dashboard — Production-Grade PostgreSQL Schema Design
**Version:** 1.0.0 | **Date:** 2026-03-30 | **Classification:** Fintech-Audit Ready

---

## Table of Contents
1. [High-Level Architecture](#1-high-level-architecture)
2. [Core Design Principles](#2-core-design-principles)
3. [Step-by-Step Reasoning Behind Major Decisions](#3-step-by-step-reasoning-behind-major-decisions)
4. [Audit Requirement Satisfaction](#4-audit-requirement-satisfaction)
5. [Read-Heavy Optimization](#5-read-heavy-optimization)
6. [Entity Design Breakdown](#6-entity-design-breakdown)
7. [PostgreSQL DDL — Complete & Production-Ready](#7-postgresql-ddl--complete--production-ready)
8. [Session Management Design](#8-session-management-design)
9. [Data Consistency Strategy](#9-data-consistency-strategy)
10. [Handling API Variability](#10-handling-api-variability)
11. [Example Flows](#11-example-flows)
12. [SQLAlchemy Models](#12-sqlalchemy-models)

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CA Firm Dashboard                            │
│        (One internal user; manages 100s of GST clients)            │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP
┌────────────────────────────▼────────────────────────────────────────┐
│                     Our Backend Service                             │
│   ┌──────────────┐   ┌───────────────┐   ┌────────────────────┐    │
│   │  Session Mgr │   │ API Proxy Layer│   │  Response Parser   │    │
│   └──────┬───────┘   └───────┬───────┘   └─────────┬──────────┘    │
│          │                   │                     │               │
│   ┌──────▼───────────────────▼─────────────────────▼──────────┐    │
│   │                     PostgreSQL                             │    │
│   │  clients  │  client_sessions  │  gstr1_*  │  gstr2a_*    │    │
│   │  gstr2b   │  gstr3b_*         │  gstr9_*  │  ledger_*    │    │
│   │  gst_return_status            │  otp_requests             │    │
│   └────────────────────────────────────────────────────────────┘    │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ HTTPS
┌─────────────────────────────▼───────────────────────────────────────┐
│               GST Sandbox API (External)                            │
│  auth/ │ gstr1/ │ gstr2a/ │ gstr2b/ │ gstr3b/ │ gstr9/ │ ledgers/ │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Architectural Points:**
- Each **client** is a GST taxpayer with a unique GSTIN registered in this dashboard.
- The backend holds **one active session per client** at any time (OTP-based tokens).
- All API responses are **parsed before storage** — the `raw` field from service functions is never persisted.
- Every table enforces a **composite unique constraint** matching the exact input parameters of its corresponding API endpoint, guaranteeing one row per logical request.
- The schema is designed to be the single source of truth for the dashboard, with read performance as the primary optimization target.

---

## 2. Core Design Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| 1 | **One row per logical request** | Identical inputs → same row (upsert). No history accumulation. |
| 2 | **No NULL in unique keys** | NULLs are never EQUAL in PostgreSQL. Optional params are stored as `NOT NULL DEFAULT ''` (empty string sentinel). |
| 3 | **No hashing** | Composite natural key constraints are used directly. Fully auditable, no collision risk. |
| 4 | **Parsed-only storage** | Raw API payloads are never stored. Only the structured parsed output is persisted. |
| 5 | **Structured columns for aggregations** | Fields used in `GROUP BY`, `SUM`, `WHERE` filters are structured columns. Deeply nested data goes to JSONB. |
| 6 | **Single active session per client** | Enforced via partial unique index `WHERE is_active = TRUE`. |
| 7 | **Explicit NOT NULL enforcement** | Every field that must exist for the row to be meaningful is `NOT NULL`. |
| 8 | **Financial year vs calendar period** | GSTR9 uses `financial_year` (`VARCHAR(7)`, e.g. `'2023-24'`). All others use `year + month`. |
| 9 | **Sentinel value pattern for optional filters** | Empty string `''` = "this filter was not applied". Included in composite unique key. |

---

## 3. Step-by-Step Reasoning Behind Major Decisions

### Decision 1: One Table Per API Endpoint, Not One Mega Table
**Problem:** All endpoints could theoretically be jammed into a single `api_responses(client_id, endpoint, params, data JSONB)` table.
**Why rejected:** Completely JSONB tables cannot enforce column-level NOT NULL, CHECK constraints, or efficient indexing on aggregated numeric fields. Dashboard queries like "show total IGST for all clients in March 2024" would require `data->>'total_igst'` with no index support. Fintech audits require schema-enforced data types.
**Decision:** Dedicated table per endpoint. Aggregation fields as typed columns. Deep-nested structures as JSONB.

### Decision 2: Empty String Sentinel for Optional Filter Parameters
**Problem:** `UNIQUE(client_id, year, month, counterparty_gstin)` — if `counterparty_gstin` is NULL, PostgreSQL will allow multiple rows with `(client1, 2024, 03, NULL)` because `NULL != NULL`.
**Why not COALESCE in index:** A functional index with COALESCE is a work-around, but it means the application can insert `NULL` and silently break idempotency if the index is missed.
**Decision:** Store all optional filter columns as `VARCHAR NOT NULL DEFAULT ''`. Application layer **must** normalize `None/null` → `''` before upsert. Constraint is then a plain column constraint, not a functional one. This is fully auditable and transparent.

### Decision 3: JSONB for Nested Arrays, Structured Columns for Dashboard Metrics
**Rule applied:**
- If a field appears in `SELECT SUM(...)`, `WHERE x > value`, or `GROUP BY` → structured typed column.
- If a field is an array of objects (invoice line items, transaction entries, error details) → JSONB.
- If a field is a deeply nested object with many sub-keys used only for display → JSONB.

**Examples:**
- `total_igst NUMERIC(15,2)` on `gstr1_b2b` → structured (used in dashboard totals)
- `invoices JSONB` on `gstr1_b2b` → JSONB (detailed invoice list, displayed on drill-down)
- `supply_details JSONB` on `gstr3b_details` → JSONB (complex nested object, not aggregated at DB level)
- `cash_balance_igst_total NUMERIC(15,2)` on `ledger_balance` → structured (balance monitoring)

### Decision 4: GSTR2B Discriminator Pattern
**Problem:** `get_gstr2b()` returns three structurally different shapes: `summary`, `documents`, and `pagination_required`. Storing in three tables creates JOIN complexity. Storing in one table with all nullable columns creates ambiguity.
**Decision:** Single `gstr2b` table with a `response_type VARCHAR(20) CHECK IN ('summary', 'documents', 'pagination_required')` discriminator. Columns for each shape are JSONB (nullable), and the `response_type` column makes it unambiguous which columns are populated. The unique key is `(client_id, year, month, file_number)` where `file_number = ''` for the non-paginated summary case.

### Decision 5: Ledger Tables Use Date Strings, Not DATE type
**Problem:** The GST API accepts dates as `DD/MM/YYYY` strings. Converting to PostgreSQL `DATE` type for storage and back for API calls introduces transformation risk and format ambiguity.
**Decision:** Store `from_date`, `to_date` as `VARCHAR(10)` matching the exact API format. The unique key uses these strings directly. No transformation, no ambiguity. If date-range indexing is later needed, a computed `DATE` column can be added.

### Decision 6: `fetched_at` vs `updated_at`
- `fetched_at`: The timestamp when the row was **first created** (first time this logical request was stored).
- `updated_at`: The timestamp of the **most recent upsert** (most recent re-fetch).
- Together they give the full lifecycle: "when was this first fetched, and how stale is the current data?"

---

## 4. Audit Requirement Satisfaction

| Audit Requirement | How Satisfied |
|-------------------|---------------|
| No duplicate rows for same logical request | Composite UNIQUE constraint on every table — DB engine rejects duplicate inserts |
| No raw payload storage | Parsed service output only; `raw` field from parsers is explicitly excluded |
| Session tokens traceable | `client_sessions` table with `created_at`, `updated_at`, `is_active` — full lifecycle |
| Only one active session per client | Partial unique index `WHERE is_active = TRUE` on `client_sessions(client_id)` |
| Data types are strict | `NUMERIC(15,2)` for money, `CHAR(15)` for GSTIN with CHECK on length, `BOOLEAN` for flags |
| Optional filters properly handled | NOT NULL + sentinel `''` pattern — no silent NULL equality bypass |
| Immutable business keys | GSTIN stored in `CHAR(15)` with `CHECK(LENGTH(gstin) = 15)` |
| Session expiry enforced | `token_expiry` and `session_expiry` columns on `client_sessions` |
| History of OTP attempts | `otp_requests` table with status lifecycle |

---

## 5. Read-Heavy Optimization

The dashboard runs aggregation, cross-client comparison, and period-filtering queries. Every optimization decision is made with this in mind.

**Composite Indexes on Partition Keys:**
All data tables have a `(client_id, year, month)` or `(client_id, financial_year)` index as the primary access pattern.

**Partial Indexes for Common Filtered Queries:**
- `gstr1_b2b` base query (no optional filters): partial index `WHERE filter_action_required = '' AND filter_from_date = '' AND filter_counterparty_gstin = ''`
- `gstr2b` summary fetch: partial index `WHERE response_type = 'summary' AND file_number = ''`
- Active sessions: partial index `WHERE is_active = TRUE`

**Structured Aggregate Columns:**
GSTR1 B2B stores `total_invoices`, `total_taxable_value`, `total_cgst`, `total_sgst`, `total_igst` as typed columns so the dashboard summary card query is `SELECT SUM(total_igst)` — no JSONB extraction required.

**JSONB GIN Indexing (optional, for search use cases):**
JSONB columns on high-volume tables can have GIN indexes added if the application needs to search within them (e.g., find a specific invoice number across B2B records).

---

## 6. Entity Design Breakdown

### 6.1 Foundation Layer

#### `clients`
Represents a GST taxpayer client managed by the CA firm. Identified by `gstin`.
- **Why `CHAR(15)` for gstin:** GSTIN is always exactly 15 characters — CHAR enforces this at the type level, and the CHECK constraint double-validates it.
- **Why no password/auth fields:** Client authentication is purely via OTP through the GST portal. There is no app-level password.

#### `client_sessions`
Holds the current session tokens obtained after OTP verification.
- **One active session per client:** Partial unique index prevents two rows with `is_active = TRUE` for the same client. When a new session is created, the old one is deactivated first.
- **`refresh_token`:** Nullable — the GST refresh endpoint may not always return a new refresh token.

#### `otp_requests`
Audit log of OTP requests. Does not enforce a unique constraint (multiple OTP requests per client over time are normal and expected). Tracks status lifecycle: `pending → verified / failed / expired`.

### 6.2 GSTR1 Layer (13 tables)

| Table | Natural Key | Optional Filters in Key |
|-------|-------------|--------------------------|
| `gstr1_advance_tax` | (client_id, year, month) | — |
| `gstr1_b2b` | (client_id, year, month) | filter_action_required, filter_from_date, filter_counterparty_gstin |
| `gstr1_summary` | (client_id, year, month, summary_type) | — (summary_type always present) |
| `gstr1_b2csa` | (client_id, year, month) | — |
| `gstr1_b2cs` | (client_id, year, month) | — |
| `gstr1_cdnr` | (client_id, year, month) | filter_action_required, filter_from_date |
| `gstr1_doc_issue` | (client_id, year, month) | — |
| `gstr1_hsn` | (client_id, year, month) | — |
| `gstr1_nil` | (client_id, year, month) | — |
| `gstr1_b2cl` | (client_id, year, month) | — |
| `gstr1_cdnur` | (client_id, year, month) | — |
| `gstr1_exp` | (client_id, year, month) | — |
| `gstr1_txp` | (client_id, year, month) | filter_counterparty_gstin, filter_action_required, filter_from_date |

### 6.3 GSTR2A Layer (7 tables)

| Table | Natural Key | Optional Filters in Key |
|-------|-------------|--------------------------|
| `gstr2a_b2b` | (client_id, year, month) | — |
| `gstr2a_b2ba` | (client_id, year, month) | filter_counterparty_gstin |
| `gstr2a_cdn` | (client_id, year, month) | filter_counterparty_gstin, filter_from_date |
| `gstr2a_cdna` | (client_id, year, month) | filter_counterparty_gstin |
| `gstr2a_document` | (client_id, year, month) | — |
| `gstr2a_isd` | (client_id, year, month) | filter_counterparty_gstin |
| `gstr2a_tds` | (client_id, year, month) | — |

### 6.4 GSTR2B Layer (2 tables)

| Table | Natural Key | Notes |
|-------|-------------|-------|
| `gstr2b` | (client_id, year, month, file_number) | `file_number = ''` for non-paginated; discriminator column `response_type` |
| `gstr2b_regen_status` | (client_id, reference_id) | reference_id from API call |

### 6.5 GSTR3B Layer (2 tables)

| Table | Natural Key |
|-------|-------------|
| `gstr3b_details` | (client_id, year, month) |
| `gstr3b_auto_liability` | (client_id, year, month) |

### 6.6 GSTR9 Layer (3 tables, financial_year keyed)

| Table | Natural Key | Notes |
|-------|-------------|-------|
| `gstr9_auto_calculated` | (client_id, financial_year) | financial_year = '2023-24' |
| `gstr9_table8a` | (client_id, financial_year, file_number) | `file_number = ''` when not paginated |
| `gstr9_details` | (client_id, financial_year) | — |

### 6.7 Ledger Layer (4 tables)

| Table | Natural Key | Notes |
|-------|-------------|-------|
| `ledger_balance` | (client_id, year, month) | Structured columns for all balance heads |
| `ledger_cash` | (client_id, from_date, to_date) | Date strings as-is from API |
| `ledger_itc` | (client_id, from_date, to_date) | Opening/closing structured; transactions JSONB |
| `ledger_liability` | (client_id, year, month, from_date, to_date) | Both period and date-range required |

### 6.8 Return Status Layer (1 table)

| Table | Natural Key |
|-------|-------------|
| `gst_return_status` | (client_id, year, month, reference_id) |

---

## 7. PostgreSQL DDL — Complete & Production-Ready

```sql
-- =====================================================================
-- GST DASHBOARD — PRODUCTION DDL
-- PostgreSQL 14+
-- All constraints are named for auditability.
-- All optional filter columns use NOT NULL DEFAULT '' sentinel pattern.
-- =====================================================================

-- Enable UUID extension if needed later
-- CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================================
-- SECTION 1: FOUNDATION — CLIENTS & SESSIONS
-- =====================================================================

CREATE TABLE clients (
    id              BIGSERIAL       PRIMARY KEY,
    gstin           CHAR(15)        NOT NULL,
    username        VARCHAR(100)    NOT NULL,
    trade_name      VARCHAR(255),
    legal_name      VARCHAR(255),
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_clients_gstin
        UNIQUE (gstin),
    CONSTRAINT ck_clients_gstin_length
        CHECK (LENGTH(TRIM(gstin)) = 15)
);

COMMENT ON TABLE  clients IS 'Each GST taxpayer client managed by the CA firm.';
COMMENT ON COLUMN clients.gstin IS 'Goods and Services Tax Identification Number — exactly 15 chars.';
COMMENT ON COLUMN clients.username IS 'GST portal username associated with this GSTIN.';


CREATE TABLE client_sessions (
    id              BIGSERIAL       PRIMARY KEY,
    client_id       BIGINT          NOT NULL,
    access_token    TEXT            NOT NULL,
    refresh_token   TEXT,
    token_expiry    TIMESTAMPTZ,
    session_expiry  TIMESTAMPTZ,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_client_sessions_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT
);

-- CRITICAL: Enforces maximum one active session per client at the DB level.
CREATE UNIQUE INDEX uq_client_sessions_one_active
    ON client_sessions(client_id)
    WHERE is_active = TRUE;

CREATE INDEX idx_client_sessions_client_id
    ON client_sessions(client_id);

CREATE INDEX idx_client_sessions_expiry_active
    ON client_sessions(session_expiry)
    WHERE is_active = TRUE;

COMMENT ON TABLE  client_sessions IS 'OTP-verified session tokens per client. At most one row with is_active=TRUE per client.';
COMMENT ON COLUMN client_sessions.is_active IS 'FALSE = deactivated (session expired or replaced). TRUE = currently valid.';


CREATE TABLE otp_requests (
    id              BIGSERIAL       PRIMARY KEY,
    client_id       BIGINT          NOT NULL,
    status          VARCHAR(20)     NOT NULL DEFAULT 'pending',
    upstream_status_cd VARCHAR(10),
    message         TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,

    CONSTRAINT fk_otp_requests_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT ck_otp_requests_status
        CHECK (status IN ('pending', 'verified', 'expired', 'failed'))
);

CREATE INDEX idx_otp_requests_client_id ON otp_requests(client_id);

COMMENT ON TABLE otp_requests IS 'Audit log of all OTP generation and verification attempts per client.';


-- =====================================================================
-- SECTION 2: GSTR1 TABLES (13 endpoints)
--
-- Design rules applied to all GSTR1 tables:
--   - Natural key: (client_id, year, month) — always present
--   - Optional filter params: NOT NULL DEFAULT '' sentinel
--   - Numeric aggregate fields: structured NUMERIC(15,2) columns
--   - Record arrays / item lists: JSONB
--   - year: VARCHAR(4) e.g. '2024'
--   - month: VARCHAR(2) e.g. '03' (zero-padded)
-- =====================================================================

-- 2.1 GSTR1 Advance Tax
CREATE TABLE gstr1_advance_tax (
    id                      BIGSERIAL       PRIMARY KEY,
    client_id               BIGINT          NOT NULL,
    year                    VARCHAR(4)      NOT NULL,
    month                   VARCHAR(2)      NOT NULL,
    -- Parsed records array: [{place_of_supply, supply_type, items:[{rate,taxable_value,igst,...}]}]
    records                 JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code    INT,
    fetched_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr1_at_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr1_advance_tax
        UNIQUE (client_id, year, month)
);

CREATE INDEX idx_gstr1_at_period ON gstr1_advance_tax(client_id, year, month);

-- 2.2 GSTR1 B2B
-- Optional query params from OpenAPI: action_required, from_date, counterparty_gstin
-- Each unique combination is a distinct logical request — stored as separate row.
CREATE TABLE gstr1_b2b (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    year                        VARCHAR(4)      NOT NULL,
    month                       VARCHAR(2)      NOT NULL,
    -- Optional filter params ('' = not provided by caller)
    filter_action_required      VARCHAR(1)      NOT NULL DEFAULT '',
    filter_from_date            VARCHAR(10)     NOT NULL DEFAULT '',
    filter_counterparty_gstin   VARCHAR(15)     NOT NULL DEFAULT '',
    -- Structured aggregate columns for dashboard summary cards
    total_invoices              INT,
    total_taxable_value         NUMERIC(15,2),
    total_cgst                  NUMERIC(15,2),
    total_sgst                  NUMERIC(15,2),
    total_igst                  NUMERIC(15,2),
    -- Full invoice details: [{counterparty_gstin, invoice_number, invoice_date, invoice_value, items:[...]}]
    invoices                    JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr1_b2b_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr1_b2b
        UNIQUE (client_id, year, month,
                filter_action_required, filter_from_date, filter_counterparty_gstin),
    CONSTRAINT ck_gstr1_b2b_action_required
        CHECK (filter_action_required IN ('', 'Y', 'N')),
    CONSTRAINT ck_gstr1_b2b_counterparty_gstin_len
        CHECK (filter_counterparty_gstin = '' OR LENGTH(filter_counterparty_gstin) = 15)
);

CREATE INDEX idx_gstr1_b2b_period ON gstr1_b2b(client_id, year, month);

-- Partial index for the most common case: no filters applied (base fetch)
CREATE INDEX idx_gstr1_b2b_base_fetch ON gstr1_b2b(client_id, year, month)
    WHERE filter_action_required = ''
      AND filter_from_date = ''
      AND filter_counterparty_gstin = '';

-- 2.3 GSTR1 Summary
-- summary_type is always present (defaults to 'short') — included directly in unique key
CREATE TABLE gstr1_summary (
    id                      BIGSERIAL       PRIMARY KEY,
    client_id               BIGINT          NOT NULL,
    year                    VARCHAR(4)      NOT NULL,
    month                   VARCHAR(2)      NOT NULL,
    summary_type            VARCHAR(5)      NOT NULL DEFAULT 'short',
    ret_period              VARCHAR(10),
    -- sections: [{sec_nm, ttl_rec, ttl_val, ttl_tax}]
    sections                JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code    INT,
    fetched_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr1_summary_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr1_summary
        UNIQUE (client_id, year, month, summary_type),
    CONSTRAINT ck_gstr1_summary_type
        CHECK (summary_type IN ('short', 'long'))
);

CREATE INDEX idx_gstr1_summary_period ON gstr1_summary(client_id, year, month);

-- 2.4 GSTR1 B2CSA
CREATE TABLE gstr1_b2csa (
    id                      BIGSERIAL       PRIMARY KEY,
    client_id               BIGINT          NOT NULL,
    year                    VARCHAR(4)      NOT NULL,
    month                   VARCHAR(2)      NOT NULL,
    -- records: [{pos, supply_type, invoice_type, rt, txval, iamt, camt, samt, csamt}]
    records                 JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code    INT,
    fetched_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr1_b2csa_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr1_b2csa
        UNIQUE (client_id, year, month)
);

-- 2.5 GSTR1 B2CS
CREATE TABLE gstr1_b2cs (
    id                      BIGSERIAL       PRIMARY KEY,
    client_id               BIGINT          NOT NULL,
    year                    VARCHAR(4)      NOT NULL,
    month                   VARCHAR(2)      NOT NULL,
    -- records: [{place_of_supply, supply_type, invoice_type, tax_rate, taxable_value, igst, cgst, sgst, cess, ...}]
    records                 JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code    INT,
    fetched_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr1_b2cs_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr1_b2cs
        UNIQUE (client_id, year, month)
);

-- 2.6 GSTR1 CDNR
-- Optional params from OpenAPI: action_required (Y/N), from (DD/MM/YYYY)
CREATE TABLE gstr1_cdnr (
    id                      BIGSERIAL       PRIMARY KEY,
    client_id               BIGINT          NOT NULL,
    year                    VARCHAR(4)      NOT NULL,
    month                   VARCHAR(2)      NOT NULL,
    filter_action_required  VARCHAR(1)      NOT NULL DEFAULT '',
    filter_from_date        VARCHAR(10)     NOT NULL DEFAULT '',
    record_count            INT,
    -- records: [{counterparty_gstin, note_number, note_date, note_type, items:[...]}]
    records                 JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code    INT,
    fetched_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr1_cdnr_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr1_cdnr
        UNIQUE (client_id, year, month, filter_action_required, filter_from_date),
    CONSTRAINT ck_gstr1_cdnr_action
        CHECK (filter_action_required IN ('', 'Y', 'N'))
);

CREATE INDEX idx_gstr1_cdnr_period ON gstr1_cdnr(client_id, year, month);

-- 2.7 GSTR1 Document Issue
CREATE TABLE gstr1_doc_issue (
    id                      BIGSERIAL       PRIMARY KEY,
    client_id               BIGINT          NOT NULL,
    year                    VARCHAR(4)      NOT NULL,
    month                   VARCHAR(2)      NOT NULL,
    -- records: [{document_type_number, serial_number, from_serial, to_serial, total_issued, cancelled, net_issued}]
    records                 JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code    INT,
    fetched_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr1_doc_issue_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr1_doc_issue
        UNIQUE (client_id, year, month)
);

-- 2.8 GSTR1 HSN Summary
CREATE TABLE gstr1_hsn (
    id                      BIGSERIAL       PRIMARY KEY,
    client_id               BIGINT          NOT NULL,
    year                    VARCHAR(4)      NOT NULL,
    month                   VARCHAR(2)      NOT NULL,
    -- records: [{serial_number, hsn_sac_code, description, unit_of_quantity, quantity, tax_rate, taxable_value, igst, cgst, sgst}]
    records                 JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code    INT,
    fetched_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr1_hsn_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr1_hsn
        UNIQUE (client_id, year, month)
);

-- 2.9 GSTR1 Nil Rated
CREATE TABLE gstr1_nil (
    id                      BIGSERIAL       PRIMARY KEY,
    client_id               BIGINT          NOT NULL,
    year                    VARCHAR(4)      NOT NULL,
    month                   VARCHAR(2)      NOT NULL,
    -- records: [{supply_type_code, supply_type, nil_rated_amount, exempted_amount, non_gst_amount}]
    records                 JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code    INT,
    fetched_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr1_nil_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr1_nil
        UNIQUE (client_id, year, month)
);

-- 2.10 GSTR1 B2CL (Large Unregistered)
CREATE TABLE gstr1_b2cl (
    id                      BIGSERIAL       PRIMARY KEY,
    client_id               BIGINT          NOT NULL,
    year                    VARCHAR(4)      NOT NULL,
    month                   VARCHAR(2)      NOT NULL,
    records                 JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code    INT,
    fetched_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr1_b2cl_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr1_b2cl
        UNIQUE (client_id, year, month)
);

-- 2.11 GSTR1 CDNUR (Credit/Debit Notes Unregistered)
CREATE TABLE gstr1_cdnur (
    id                      BIGSERIAL       PRIMARY KEY,
    client_id               BIGINT          NOT NULL,
    year                    VARCHAR(4)      NOT NULL,
    month                   VARCHAR(2)      NOT NULL,
    records                 JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code    INT,
    fetched_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr1_cdnur_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr1_cdnur
        UNIQUE (client_id, year, month)
);

-- 2.12 GSTR1 EXP (Exports)
CREATE TABLE gstr1_exp (
    id                      BIGSERIAL       PRIMARY KEY,
    client_id               BIGINT          NOT NULL,
    year                    VARCHAR(4)      NOT NULL,
    month                   VARCHAR(2)      NOT NULL,
    -- records: [{export_type_code, export_type, invoice_number, invoice_date, invoice_value, flag, items:[...]}]
    records                 JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code    INT,
    fetched_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr1_exp_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr1_exp
        UNIQUE (client_id, year, month)
);

-- 2.13 GSTR1 TXP (Tax Payments / Advance Tax Adjustments)
-- Optional params: counterparty_gstin, action_required, from_date
CREATE TABLE gstr1_txp (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    year                        VARCHAR(4)      NOT NULL,
    month                       VARCHAR(2)      NOT NULL,
    filter_counterparty_gstin   VARCHAR(15)     NOT NULL DEFAULT '',
    filter_action_required      VARCHAR(1)      NOT NULL DEFAULT '',
    filter_from_date            VARCHAR(10)     NOT NULL DEFAULT '',
    records                     JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr1_txp_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr1_txp
        UNIQUE (client_id, year, month,
                filter_counterparty_gstin, filter_action_required, filter_from_date),
    CONSTRAINT ck_gstr1_txp_action
        CHECK (filter_action_required IN ('', 'Y', 'N')),
    CONSTRAINT ck_gstr1_txp_counterparty_len
        CHECK (filter_counterparty_gstin = '' OR LENGTH(filter_counterparty_gstin) = 15)
);

CREATE INDEX idx_gstr1_txp_period ON gstr1_txp(client_id, year, month);


-- =====================================================================
-- SECTION 3: GSTR2A TABLES (7 endpoints)
-- =====================================================================

-- 3.1 GSTR2A B2B
CREATE TABLE gstr2a_b2b (
    id                      BIGSERIAL       PRIMARY KEY,
    client_id               BIGINT          NOT NULL,
    year                    VARCHAR(4)      NOT NULL,
    month                   VARCHAR(2)      NOT NULL,
    -- records: [{supplier_gstin, filing_status_gstr1, invoice_number, invoice_date, items:[...]}]
    records                 JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code    INT,
    fetched_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr2a_b2b_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr2a_b2b
        UNIQUE (client_id, year, month)
);

CREATE INDEX idx_gstr2a_b2b_period ON gstr2a_b2b(client_id, year, month);

-- 3.2 GSTR2A B2BA (Amended B2B)
-- Optional filter: counterparty_gstin
CREATE TABLE gstr2a_b2ba (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    year                        VARCHAR(4)      NOT NULL,
    month                       VARCHAR(2)      NOT NULL,
    filter_counterparty_gstin   VARCHAR(15)     NOT NULL DEFAULT '',
    records                     JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr2a_b2ba_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr2a_b2ba
        UNIQUE (client_id, year, month, filter_counterparty_gstin),
    CONSTRAINT ck_gstr2a_b2ba_counterparty_len
        CHECK (filter_counterparty_gstin = '' OR LENGTH(filter_counterparty_gstin) = 15)
);

-- 3.3 GSTR2A CDN (Credit/Debit Notes Registered)
-- Optional filters: counterparty_gstin, from_date
CREATE TABLE gstr2a_cdn (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    year                        VARCHAR(4)      NOT NULL,
    month                       VARCHAR(2)      NOT NULL,
    filter_counterparty_gstin   VARCHAR(15)     NOT NULL DEFAULT '',
    filter_from_date            VARCHAR(10)     NOT NULL DEFAULT '',
    records                     JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr2a_cdn_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr2a_cdn
        UNIQUE (client_id, year, month, filter_counterparty_gstin, filter_from_date),
    CONSTRAINT ck_gstr2a_cdn_counterparty_len
        CHECK (filter_counterparty_gstin = '' OR LENGTH(filter_counterparty_gstin) = 15)
);

CREATE INDEX idx_gstr2a_cdn_period ON gstr2a_cdn(client_id, year, month);

-- 3.4 GSTR2A CDNA (Amended CDN)
-- Optional filter: counterparty_gstin
CREATE TABLE gstr2a_cdna (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    year                        VARCHAR(4)      NOT NULL,
    month                       VARCHAR(2)      NOT NULL,
    filter_counterparty_gstin   VARCHAR(15)     NOT NULL DEFAULT '',
    records                     JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr2a_cdna_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr2a_cdna
        UNIQUE (client_id, year, month, filter_counterparty_gstin),
    CONSTRAINT ck_gstr2a_cdna_counterparty_len
        CHECK (filter_counterparty_gstin = '' OR LENGTH(filter_counterparty_gstin) = 15)
);

-- 3.5 GSTR2A Document (Consolidated: B2B + B2BA + CDN in one call)
CREATE TABLE gstr2a_document (
    id                      BIGSERIAL       PRIMARY KEY,
    client_id               BIGINT          NOT NULL,
    year                    VARCHAR(4)      NOT NULL,
    month                   VARCHAR(2)      NOT NULL,
    b2b                     JSONB           NOT NULL DEFAULT '[]',
    b2ba                    JSONB           NOT NULL DEFAULT '[]',
    cdn                     JSONB           NOT NULL DEFAULT '[]',
    summary_all             JSONB,
    summary_pending_action  JSONB,
    upstream_status_code    INT,
    fetched_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr2a_document_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr2a_document
        UNIQUE (client_id, year, month)
);

-- 3.6 GSTR2A ISD (Input Service Distributor)
-- Optional filter: counterparty_gstin
CREATE TABLE gstr2a_isd (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    year                        VARCHAR(4)      NOT NULL,
    month                       VARCHAR(2)      NOT NULL,
    filter_counterparty_gstin   VARCHAR(15)     NOT NULL DEFAULT '',
    -- records: [{isd_gstin, document_number, document_date, document_type, itc_available, igst, cgst, sgst, cess}]
    records                     JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr2a_isd_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr2a_isd
        UNIQUE (client_id, year, month, filter_counterparty_gstin),
    CONSTRAINT ck_gstr2a_isd_counterparty_len
        CHECK (filter_counterparty_gstin = '' OR LENGTH(filter_counterparty_gstin) = 15)
);

-- 3.7 GSTR2A TDS
CREATE TABLE gstr2a_tds (
    id                              BIGSERIAL       PRIMARY KEY,
    client_id                       BIGINT          NOT NULL,
    year                            VARCHAR(4)      NOT NULL,
    month                           VARCHAR(2)      NOT NULL,
    entry_count                     INT,
    -- Structured grand totals for dashboard aggregations
    grand_total_deduction_base      NUMERIC(15,2),
    grand_total_igst                NUMERIC(15,2),
    grand_total_cgst                NUMERIC(15,2),
    grand_total_sgst                NUMERIC(15,2),
    grand_total_tds_credit          NUMERIC(15,2),
    -- Normalized TDS entries array
    tds_entries                     JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code            INT,
    fetched_at                      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr2a_tds_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr2a_tds
        UNIQUE (client_id, year, month)
);


-- =====================================================================
-- SECTION 4: GSTR2B TABLE
--
-- Single table with discriminator pattern.
-- response_type: 'summary' | 'documents' | 'pagination_required'
-- file_number: '' (no pagination) or actual file number for paginated docs.
-- Unique key: (client_id, year, month, file_number)
-- Summary response → file_number = '', response_type = 'summary'
-- Paginated doc  → file_number = '1', response_type = 'documents'
-- =====================================================================

CREATE TABLE gstr2b (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    year                        VARCHAR(4)      NOT NULL,
    month                       VARCHAR(2)      NOT NULL,
    -- file_number: '' for non-paginated; '1', '2', ... for paginated pages
    file_number                 VARCHAR(20)     NOT NULL DEFAULT '',
    -- Discriminator — determines which JSONB columns are populated
    response_type               VARCHAR(25)     NOT NULL,
    -- Common metadata fields
    return_period               VARCHAR(10),
    gen_date                    VARCHAR(30),
    version                     VARCHAR(20),
    checksum                    VARCHAR(100),
    file_count                  INT,
    pagination_required         BOOLEAN         NOT NULL DEFAULT FALSE,
    -- Populated when response_type = 'summary'
    counterparty_summary        JSONB,          -- {b2b: parsed, cdnr: parsed}
    -- Populated when response_type = 'summary' OR 'documents'
    itc_summary                 JSONB,
    -- Populated when response_type = 'documents'
    b2b                         JSONB,          -- {invoices: [...], summary: {...}}
    b2ba                        JSONB,
    cdnr                        JSONB,
    cdnra                       JSONB,
    isd                         JSONB,
    grand_summary               JSONB,
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr2b_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr2b
        UNIQUE (client_id, year, month, file_number),
    CONSTRAINT ck_gstr2b_response_type
        CHECK (response_type IN ('summary', 'documents', 'pagination_required'))
);

CREATE INDEX idx_gstr2b_period ON gstr2b(client_id, year, month);

-- Fast access to the summary row (most common dashboard query)
CREATE INDEX idx_gstr2b_summary_fetch ON gstr2b(client_id, year, month)
    WHERE response_type = 'summary' AND file_number = '';


-- GSTR2B Regeneration Status
CREATE TABLE gstr2b_regen_status (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    reference_id                VARCHAR(100)    NOT NULL,
    form_type_label             VARCHAR(50),
    action                      VARCHAR(50),
    processing_status_label     VARCHAR(100),
    has_errors                  BOOLEAN,
    error_report                JSONB,
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr2b_regen_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr2b_regen_status
        UNIQUE (client_id, reference_id)
);


-- =====================================================================
-- SECTION 5: GSTR3B TABLES
-- =====================================================================

CREATE TABLE gstr3b_details (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    year                        VARCHAR(4)      NOT NULL,
    month                       VARCHAR(2)      NOT NULL,
    return_period               VARCHAR(10),
    status_cd                   VARCHAR(10),
    -- All major sections stored as JSONB — complex nested objects not aggregated at DB level
    supply_details              JSONB           NOT NULL DEFAULT '{}',
    inter_state_supplies        JSONB           NOT NULL DEFAULT '{}',
    eligible_itc                JSONB           NOT NULL DEFAULT '{}',
    inward_supplies             JSONB           NOT NULL DEFAULT '{}',
    interest_and_late_fee       JSONB           NOT NULL DEFAULT '{}',
    tax_payment                 JSONB           NOT NULL DEFAULT '{}',
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr3b_details_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr3b_details
        UNIQUE (client_id, year, month)
);

CREATE INDEX idx_gstr3b_details_period ON gstr3b_details(client_id, year, month);


CREATE TABLE gstr3b_auto_liability (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    year                        VARCHAR(4)      NOT NULL,
    month                       VARCHAR(2)      NOT NULL,
    status_cd                   VARCHAR(10),
    -- auto_calculated_liability: {liab_details: {supply, inter_sup}, elg_itc}
    auto_calculated_liability   JSONB           NOT NULL DEFAULT '{}',
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr3b_auto_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr3b_auto_liability
        UNIQUE (client_id, year, month)
);

CREATE INDEX idx_gstr3b_auto_period ON gstr3b_auto_liability(client_id, year, month);


-- =====================================================================
-- SECTION 6: GSTR9 TABLES
-- GSTR9 is annual — uses financial_year (e.g. '2023-24'), NOT year+month.
-- =====================================================================

CREATE TABLE gstr9_auto_calculated (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    -- e.g. '2023-24' — format enforced by CHECK constraint
    financial_year              VARCHAR(7)      NOT NULL,
    status_cd                   VARCHAR(10),
    financial_period            VARCHAR(20),
    aggregate_turnover          NUMERIC(18,2),
    hsn_min_length              INT,
    -- Annual table-wise sections
    table4_outward_supplies     JSONB,
    table5_exempt_nil_non_gst   JSONB,
    table6_itc_availed          JSONB,
    table8_itc_as_per_2b        JSONB,
    table9_tax_paid             JSONB,
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr9_auto_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr9_auto_calculated
        UNIQUE (client_id, financial_year),
    CONSTRAINT ck_gstr9_auto_fy_format
        CHECK (financial_year ~ '^\d{4}-\d{2}$')
);

CREATE INDEX idx_gstr9_auto_fy ON gstr9_auto_calculated(client_id, financial_year);


-- GSTR9 Table 8A — may be paginated (file_number)
CREATE TABLE gstr9_table8a (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    financial_year              VARCHAR(7)      NOT NULL,
    -- file_number: '' for non-paginated, actual number for paginated
    file_number                 VARCHAR(20)     NOT NULL DEFAULT '',
    status_cd                   VARCHAR(10),
    b2b                         JSONB           NOT NULL DEFAULT '[]',
    b2ba                        JSONB           NOT NULL DEFAULT '[]',
    cdn                         JSONB           NOT NULL DEFAULT '[]',
    -- Structured summary columns for dashboard aggregations
    summary_b2b_taxable_value   NUMERIC(15,2),
    summary_b2b_igst            NUMERIC(15,2),
    summary_b2b_cgst            NUMERIC(15,2),
    summary_b2b_sgst            NUMERIC(15,2),
    summary_b2b_cess            NUMERIC(15,2),
    summary_b2b_invoice_count   INT,
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr9_table8a_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr9_table8a
        UNIQUE (client_id, financial_year, file_number),
    CONSTRAINT ck_gstr9_table8a_fy_format
        CHECK (financial_year ~ '^\d{4}-\d{2}$')
);

CREATE INDEX idx_gstr9_table8a_fy ON gstr9_table8a(client_id, financial_year);


CREATE TABLE gstr9_details (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    financial_year              VARCHAR(7)      NOT NULL,
    status_cd                   VARCHAR(10),
    detail_sections             JSONB           NOT NULL DEFAULT '{}',
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gstr9_details_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gstr9_details
        UNIQUE (client_id, financial_year),
    CONSTRAINT ck_gstr9_details_fy_format
        CHECK (financial_year ~ '^\d{4}-\d{2}$')
);


-- =====================================================================
-- SECTION 7: LEDGER TABLES
-- =====================================================================

-- 7.1 Cash + ITC Balance (point-in-time month snapshot)
-- All tax heads structured for fast dashboard balance monitoring
CREATE TABLE ledger_balance (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    year                        VARCHAR(4)      NOT NULL,
    month                       VARCHAR(2)      NOT NULL,
    status_cd                   VARCHAR(10),
    -- Cash balance — IGST head (most granular)
    cash_igst_tax               NUMERIC(15,2),
    cash_igst_interest          NUMERIC(15,2),
    cash_igst_penalty           NUMERIC(15,2),
    cash_igst_fee               NUMERIC(15,2),
    cash_igst_other             NUMERIC(15,2),
    cash_igst_total             NUMERIC(15,2),
    -- Cash balance — other heads (total only, sub-breakdown in JSONB if needed)
    cash_cgst_total             NUMERIC(15,2),
    cash_sgst_total             NUMERIC(15,2),
    cash_cess_total             NUMERIC(15,2),
    -- ITC balance
    itc_igst                    NUMERIC(15,2),
    itc_cgst                    NUMERIC(15,2),
    itc_sgst                    NUMERIC(15,2),
    itc_cess                    NUMERIC(15,2),
    -- ITC blocked balance
    itc_blocked_igst            NUMERIC(15,2),
    itc_blocked_cgst            NUMERIC(15,2),
    itc_blocked_sgst            NUMERIC(15,2),
    itc_blocked_cess            NUMERIC(15,2),
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_ledger_balance_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_ledger_balance
        UNIQUE (client_id, year, month)
);

CREATE INDEX idx_ledger_balance_period ON ledger_balance(client_id, year, month);


-- 7.2 Cash Ledger (date-range query)
-- from_date and to_date are REQUIRED inputs from API — stored as-is (DD/MM/YYYY)
CREATE TABLE ledger_cash (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    from_date                   VARCHAR(10)     NOT NULL,
    to_date                     VARCHAR(10)     NOT NULL,
    status_cd                   VARCHAR(10),
    opening_balance             JSONB,          -- tax-head-wise blocks
    closing_balance             JSONB,
    transactions                JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_ledger_cash_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_ledger_cash
        UNIQUE (client_id, from_date, to_date)
);

CREATE INDEX idx_ledger_cash_dates ON ledger_cash(client_id, from_date, to_date);


-- 7.3 ITC Ledger (date-range query)
-- Opening/closing balances structured for quick comparisons; transactions in JSONB
CREATE TABLE ledger_itc (
    id                              BIGSERIAL       PRIMARY KEY,
    client_id                       BIGINT          NOT NULL,
    from_date                       VARCHAR(10)     NOT NULL,
    to_date                         VARCHAR(10)     NOT NULL,
    status_cd                       VARCHAR(10),
    -- Structured for fast balance comparisons on dashboard
    opening_igst                    NUMERIC(15,2),
    opening_cgst                    NUMERIC(15,2),
    opening_sgst                    NUMERIC(15,2),
    opening_cess                    NUMERIC(15,2),
    opening_total_range_balance     NUMERIC(15,2),
    closing_igst                    NUMERIC(15,2),
    closing_cgst                    NUMERIC(15,2),
    closing_sgst                    NUMERIC(15,2),
    closing_cess                    NUMERIC(15,2),
    closing_total_range_balance     NUMERIC(15,2),
    transactions                    JSONB           NOT NULL DEFAULT '[]',
    provisional_credit_balances     JSONB,
    upstream_status_code            INT,
    fetched_at                      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_ledger_itc_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_ledger_itc
        UNIQUE (client_id, from_date, to_date)
);

CREATE INDEX idx_ledger_itc_dates ON ledger_itc(client_id, from_date, to_date);


-- 7.4 Return Liability Ledger
-- Requires BOTH period (year+month) AND date range (from+to) — all four are in unique key
CREATE TABLE ledger_liability (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    year                        VARCHAR(4)      NOT NULL,
    month                       VARCHAR(2)      NOT NULL,
    from_date                   VARCHAR(10)     NOT NULL,
    to_date                     VARCHAR(10)     NOT NULL,
    status_cd                   VARCHAR(10),
    closing_balance             JSONB,          -- {igst:{...}, cgst:{...}, sgst:{...}, cess:{...}}
    transactions                JSONB           NOT NULL DEFAULT '[]',
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_ledger_liability_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_ledger_liability
        UNIQUE (client_id, year, month, from_date, to_date)
);

CREATE INDEX idx_ledger_liability_period ON ledger_liability(client_id, year, month);


-- =====================================================================
-- SECTION 8: RETURN STATUS
-- reference_id is a required input from the caller — part of unique key
-- =====================================================================

CREATE TABLE gst_return_status (
    id                          BIGSERIAL       PRIMARY KEY,
    client_id                   BIGINT          NOT NULL,
    year                        VARCHAR(4)      NOT NULL,
    month                       VARCHAR(2)      NOT NULL,
    -- reference_id returned from save/reset action — required by API
    reference_id                VARCHAR(100)    NOT NULL,
    status_cd                   VARCHAR(10),
    form_type                   VARCHAR(20),
    form_type_label             VARCHAR(50),
    action                      VARCHAR(20),
    processing_status           VARCHAR(10),
    processing_status_label     VARCHAR(100),
    has_errors                  BOOLEAN,
    -- error_report contains section-wise normalized error trees
    error_report                JSONB,
    upstream_status_code        INT,
    fetched_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_gst_return_status_client
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE RESTRICT,
    CONSTRAINT uq_gst_return_status
        UNIQUE (client_id, year, month, reference_id),
    CONSTRAINT ck_gst_return_status_processing
        CHECK (processing_status IS NULL OR
               processing_status IN ('P', 'PE', 'ER', 'REC'))
);

CREATE INDEX idx_gst_return_status_period ON gst_return_status(client_id, year, month);
CREATE INDEX idx_gst_return_status_ref    ON gst_return_status(client_id, reference_id);
CREATE INDEX idx_gst_return_status_errors ON gst_return_status(client_id, year, month)
    WHERE has_errors = TRUE;
```

---

## 8. Session Management Design

### OTP Lifecycle

```
generate_otp(gstin, username)
    → INSERT INTO otp_requests (client_id, status='pending')
    → Call upstream API

verify_otp(gstin, username, otp)
    → On success:
        UPDATE otp_requests SET status='verified' WHERE client_id = X ORDER BY created_at DESC LIMIT 1
        UPDATE client_sessions SET is_active=FALSE WHERE client_id = X AND is_active=TRUE
        INSERT INTO client_sessions (client_id, access_token, ..., is_active=TRUE)
    → On failure:
        UPDATE otp_requests SET status='failed' WHERE ...

refresh_session(gstin)
    → On success:
        UPDATE client_sessions
           SET access_token = new_token,
               refresh_token = new_refresh,
               token_expiry = new_expiry,
               updated_at = NOW()
         WHERE client_id = X AND is_active = TRUE
```

### Why Partial Unique Index for Sessions?

```sql
CREATE UNIQUE INDEX uq_client_sessions_one_active
    ON client_sessions(client_id)
    WHERE is_active = TRUE;
```

This means:
- DB enforces that only ONE row with `is_active = TRUE` can exist per `client_id`.
- Deactivated sessions (`is_active = FALSE`) are historical records — multiple allowed.
- When switching between clients on the dashboard, the backend simply reads the `access_token` from `client_sessions WHERE client_id = ? AND is_active = TRUE`.

### Session Expiry Handling

The scheduler (`session_refresh_manager.py`) calls `refresh_session(gstin)` before `token_expiry`. The `token_expiry` column in `client_sessions` is the database-stored hint for this. The scheduler queries:

```sql
SELECT c.gstin, cs.token_expiry
FROM client_sessions cs
JOIN clients c ON c.id = cs.client_id
WHERE cs.is_active = TRUE
  AND cs.token_expiry < NOW() + INTERVAL '5 minutes';
```

---

## 9. Data Consistency Strategy

### Rule: Same Request = Same Row

Every table enforces this through its composite UNIQUE constraint. The application layer executes:

```sql
INSERT INTO <table> (<all_columns>)
VALUES (<all_values>)
ON CONFLICT ON CONSTRAINT <uq_constraint_name>
DO UPDATE SET
    <data_column_1> = EXCLUDED.<data_column_1>,
    ...,
    updated_at = NOW();
```

This is a **schema-enforced** upsert. There is no application-level "check if exists then update or insert" logic — the DB engine handles it atomically.

### How Optional Filters Are Handled

Consider `gstr1_b2b`. The API accepts three optional filters. Here is how each case maps to a row:

| Call Scenario | filter_action_required | filter_from_date | filter_counterparty_gstin | Result |
|---------------|------------------------|------------------|---------------------------|--------|
| No filters | `''` | `''` | `''` | 1 row (base fetch) |
| With action_required='Y' | `'Y'` | `''` | `''` | Different row |
| With counterparty only | `''` | `''` | `'29AAAAA0000A1Z5'` | Different row |
| All three filters | `'Y'` | `'01/03/2024'` | `'29AAAAA0000A1Z5'` | Different row |
| Same as above, re-fetched | `'Y'` | `'01/03/2024'` | `'29AAAAA0000A1Z5'` | **Updates existing row** |

The empty string sentinel is the key: it is a valid, deterministic, non-NULL value that participates normally in unique constraint evaluation.

### GSTIN Validation on Clients

The GSTIN CHECK constraint at the database level prevents dirty client registration:

```sql
CONSTRAINT ck_clients_gstin_length CHECK (LENGTH(TRIM(gstin)) = 15)
```

The application layer should further validate the GSTIN structure (e.g., regex `^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$`) before inserting, but the DB provides the last-line defence.

---

## 10. Handling API Variability

### Different Response Shapes

| API | Shape | Strategy |
|-----|-------|----------|
| GSTR1 B2B | Invoices + summary | Summary in typed columns; invoices in JSONB |
| GSTR1 Summary | Sections array | Flat JSONB array with consistent objects |
| GSTR2B | 3 variants (summary/documents/pagination) | Single table with `response_type` discriminator |
| GSTR3B | Deep nested sections | Each section is a named JSONB column |
| GSTR9 Auto | Annual table-wise blocks | One JSONB column per table section |
| Ledger Balance | Tax-head structured | All heads as typed `NUMERIC(15,2)` columns |
| Ledger Cash/ITC | Opening/closing + transactions | Balances structured; transactions JSONB |
| Return Status | Error report tree | `has_errors BOOLEAN` structured; full tree in JSONB |

### JSONB vs Structured Columns: Final Decision Matrix

| Use JSONB when… | Use typed columns when… |
|-----------------|------------------------|
| Array of invoice/note/entry objects | Tax amounts used in SUM/GROUP BY |
| Error report tree (display only) | Status codes used in WHERE filters |
| Sub-sections not aggregated at DB | Count fields used in ordering |
| Deeply nested objects (3+ levels) | Balance fields used in dashboard cards |
| Data shape may evolve upstream | Primary key and FK fields |

---

## 11. Example Flows

### Flow 1: Fetch GSTR1 B2B for a month with optional counterparty filter

**Request:** `GET /gstr1/b2b/29AAAAA0000A1Z5/2024/03?counterparty_gstin=27BBBBB1111B1Z9`

```
Input normalization (application layer):
  client_id                 = 42  (looked up by gstin)
  year                      = '2024'
  month                     = '03'
  filter_action_required    = ''   (not provided → sentinel)
  filter_from_date          = ''   (not provided → sentinel)
  filter_counterparty_gstin = '27BBBBB1111B1Z9'

DB upsert:
  INSERT INTO gstr1_b2b
      (client_id, year, month,
       filter_action_required, filter_from_date, filter_counterparty_gstin,
       total_invoices, total_taxable_value, total_cgst, total_sgst, total_igst,
       invoices, upstream_status_code, updated_at)
  VALUES
      (42, '2024', '03', '', '', '27BBBBB1111B1Z9',
       12, 480000.00, 43200.00, 43200.00, 0.00,
       '[{"invoice_number":"INV001",...}]', 200, NOW())
  ON CONFLICT ON CONSTRAINT uq_gstr1_b2b
  DO UPDATE SET
      total_invoices        = EXCLUDED.total_invoices,
      total_taxable_value   = EXCLUDED.total_taxable_value,
      total_cgst            = EXCLUDED.total_cgst,
      total_sgst            = EXCLUDED.total_sgst,
      total_igst            = EXCLUDED.total_igst,
      invoices              = EXCLUDED.invoices,
      upstream_status_code  = EXCLUDED.upstream_status_code,
      updated_at            = NOW();

Row identity: (42, '2024', '03', '', '', '27BBBBB1111B1Z9') → always 1 row.
Re-running the same API call updates this same row, never inserts a duplicate.
```

---

### Flow 2: Fetch GSTR2B with pagination (file_number)

**Round 1 (no file_number):** API returns `status_cd = '3'` (pagination required)

```
INSERT INTO gstr2b
    (client_id, year, month, file_number, response_type,
     return_period, file_count, pagination_required, ...)
VALUES
    (42, '2024', '03', '', 'pagination_required',
     '032024', 3, TRUE, ...)
ON CONFLICT ON CONSTRAINT uq_gstr2b DO UPDATE ...;
```

**Round 2 (file_number = '1'):** Fetch page 1

```
INSERT INTO gstr2b
    (client_id, year, month, file_number, response_type,
     b2b, b2ba, cdnr, cdnra, isd, grand_summary, itc_summary, ...)
VALUES
    (42, '2024', '03', '1', 'documents',
     '{invoices:[...]}', ..., ...)
ON CONFLICT ON CONSTRAINT uq_gstr2b DO UPDATE ...;
```

**Round 3 (file_number = '2'):** Fetch page 2

```
INSERT INTO gstr2b (..., file_number = '2', ...) ON CONFLICT DO UPDATE ...;
```

**Result:** 3 rows in `gstr2b` for (client=42, year='2024', month='03'):
- `file_number = ''` — pagination indicator
- `file_number = '1'` — page 1 documents
- `file_number = '2'` — page 2 documents

Re-fetching any page updates only that row.

---

### Flow 3: Session creation and switching between two clients

```
-- Client A (GSTIN: 29AAAAA0000A1Z5)
-- Step 1: Generate OTP
INSERT INTO otp_requests (client_id=10, status='pending') RETURNING id;

-- Step 2: Verify OTP → session established
UPDATE client_sessions SET is_active=FALSE WHERE client_id=10 AND is_active=TRUE;
INSERT INTO client_sessions
    (client_id=10, access_token='tok_A', token_expiry='...', is_active=TRUE);

-- Client B (GSTIN: 27BBBBB1111B1Z9)
-- (Same flow — no interference because partial unique index is per client_id)
UPDATE client_sessions SET is_active=FALSE WHERE client_id=11 AND is_active=TRUE;
INSERT INTO client_sessions
    (client_id=11, access_token='tok_B', token_expiry='...', is_active=TRUE);

-- Dashboard switches to Client A — read active token:
SELECT access_token, token_expiry
FROM client_sessions
WHERE client_id = 10 AND is_active = TRUE;
-- → 'tok_A'

-- Dashboard switches to Client B:
SELECT access_token, token_expiry
FROM client_sessions
WHERE client_id = 11 AND is_active = TRUE;
-- → 'tok_B'
```

---

## 12. SQLAlchemy Models

```python
"""
SQLAlchemy 2.x (async-compatible) models for GST Dashboard.
Using mapped_column() and DeclarativeBase for full type annotation support.
"""

from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, ForeignKey, Index,
    Integer, Numeric, String, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ──────────────────────────────────────────────────────────────────────
# FOUNDATION
# ──────────────────────────────────────────────────────────────────────

class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("gstin", name="uq_clients_gstin"),
        CheckConstraint("LENGTH(TRIM(gstin)) = 15", name="ck_clients_gstin_length"),
    )

    id:          Mapped[int]           = mapped_column(BigInteger, primary_key=True)
    gstin:       Mapped[str]           = mapped_column(String(15), nullable=False)
    username:    Mapped[str]           = mapped_column(String(100), nullable=False)
    trade_name:  Mapped[Optional[str]] = mapped_column(String(255))
    legal_name:  Mapped[Optional[str]] = mapped_column(String(255))
    is_active:   Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    created_at:  Mapped[datetime]      = mapped_column(TIMESTAMPTZ, nullable=False,
                                                        server_default="NOW()")
    updated_at:  Mapped[datetime]      = mapped_column(TIMESTAMPTZ, nullable=False,
                                                        server_default="NOW()")

    sessions:    Mapped[list[ClientSession]] = relationship(back_populates="client")
    otp_requests: Mapped[list[OtpRequest]]  = relationship(back_populates="client")


class ClientSession(Base):
    __tablename__ = "client_sessions"
    # Partial unique index created in migration (not in __table_args__ — partial indexes
    # require raw DDL or alembic op.create_index with postgresql_where)

    id:             Mapped[int]            = mapped_column(BigInteger, primary_key=True)
    client_id:      Mapped[int]            = mapped_column(
                        BigInteger, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    access_token:   Mapped[str]            = mapped_column(Text, nullable=False)
    refresh_token:  Mapped[Optional[str]]  = mapped_column(Text)
    token_expiry:   Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)
    session_expiry: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)
    is_active:      Mapped[bool]           = mapped_column(Boolean, nullable=False, default=True)
    created_at:     Mapped[datetime]       = mapped_column(TIMESTAMPTZ, nullable=False,
                                                            server_default="NOW()")
    updated_at:     Mapped[datetime]       = mapped_column(TIMESTAMPTZ, nullable=False,
                                                            server_default="NOW()")

    client: Mapped[Client] = relationship(back_populates="sessions")


class OtpRequest(Base):
    __tablename__ = "otp_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'verified', 'expired', 'failed')",
            name="ck_otp_requests_status",
        ),
    )

    id:                 Mapped[int]            = mapped_column(BigInteger, primary_key=True)
    client_id:          Mapped[int]            = mapped_column(
                            BigInteger, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    status:             Mapped[str]            = mapped_column(String(20), nullable=False,
                                                                default="pending")
    upstream_status_cd: Mapped[Optional[str]]  = mapped_column(String(10))
    message:            Mapped[Optional[str]]  = mapped_column(Text)
    created_at:         Mapped[datetime]       = mapped_column(TIMESTAMPTZ, nullable=False,
                                                                server_default="NOW()")
    expires_at:         Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ)

    client: Mapped[Client] = relationship(back_populates="otp_requests")


# ──────────────────────────────────────────────────────────────────────
# GSTR1 — representative models (pattern repeated for all 13 tables)
# ──────────────────────────────────────────────────────────────────────

class Gstr1B2B(Base):
    __tablename__ = "gstr1_b2b"
    __table_args__ = (
        UniqueConstraint(
            "client_id", "year", "month",
            "filter_action_required", "filter_from_date", "filter_counterparty_gstin",
            name="uq_gstr1_b2b",
        ),
        CheckConstraint(
            "filter_action_required IN ('', 'Y', 'N')",
            name="ck_gstr1_b2b_action_required",
        ),
        CheckConstraint(
            "filter_counterparty_gstin = '' OR LENGTH(filter_counterparty_gstin) = 15",
            name="ck_gstr1_b2b_counterparty_gstin_len",
        ),
        Index("idx_gstr1_b2b_period", "client_id", "year", "month"),
    )

    id:                         Mapped[int]              = mapped_column(BigInteger, primary_key=True)
    client_id:                  Mapped[int]              = mapped_column(
                                    BigInteger, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    year:                       Mapped[str]              = mapped_column(String(4), nullable=False)
    month:                      Mapped[str]              = mapped_column(String(2), nullable=False)
    filter_action_required:     Mapped[str]              = mapped_column(String(1), nullable=False, default="")
    filter_from_date:           Mapped[str]              = mapped_column(String(10), nullable=False, default="")
    filter_counterparty_gstin:  Mapped[str]              = mapped_column(String(15), nullable=False, default="")
    total_invoices:             Mapped[Optional[int]]    = mapped_column(Integer)
    total_taxable_value:        Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    total_cgst:                 Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    total_sgst:                 Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    total_igst:                 Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    invoices:                   Mapped[list]             = mapped_column(JSONB, nullable=False, default=list)
    upstream_status_code:       Mapped[Optional[int]]    = mapped_column(Integer)
    fetched_at:                 Mapped[datetime]         = mapped_column(TIMESTAMPTZ, nullable=False,
                                                                          server_default="NOW()")
    updated_at:                 Mapped[datetime]         = mapped_column(TIMESTAMPTZ, nullable=False,
                                                                          server_default="NOW()")


class Gstr1Summary(Base):
    __tablename__ = "gstr1_summary"
    __table_args__ = (
        UniqueConstraint("client_id", "year", "month", "summary_type",
                         name="uq_gstr1_summary"),
        CheckConstraint("summary_type IN ('short', 'long')",
                        name="ck_gstr1_summary_type"),
    )

    id:                   Mapped[int]           = mapped_column(BigInteger, primary_key=True)
    client_id:            Mapped[int]           = mapped_column(
                              BigInteger, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    year:                 Mapped[str]           = mapped_column(String(4), nullable=False)
    month:                Mapped[str]           = mapped_column(String(2), nullable=False)
    summary_type:         Mapped[str]           = mapped_column(String(5), nullable=False, default="short")
    ret_period:           Mapped[Optional[str]] = mapped_column(String(10))
    sections:             Mapped[list]          = mapped_column(JSONB, nullable=False, default=list)
    upstream_status_code: Mapped[Optional[int]] = mapped_column(Integer)
    fetched_at:           Mapped[datetime]      = mapped_column(TIMESTAMPTZ, nullable=False,
                                                                 server_default="NOW()")
    updated_at:           Mapped[datetime]      = mapped_column(TIMESTAMPTZ, nullable=False,
                                                                 server_default="NOW()")


# ──────────────────────────────────────────────────────────────────────
# GSTR2B — discriminator pattern model
# ──────────────────────────────────────────────────────────────────────

class Gstr2B(Base):
    __tablename__ = "gstr2b"
    __table_args__ = (
        UniqueConstraint("client_id", "year", "month", "file_number",
                         name="uq_gstr2b"),
        CheckConstraint(
            "response_type IN ('summary', 'documents', 'pagination_required')",
            name="ck_gstr2b_response_type",
        ),
        Index("idx_gstr2b_period", "client_id", "year", "month"),
    )

    id:                     Mapped[int]            = mapped_column(BigInteger, primary_key=True)
    client_id:              Mapped[int]            = mapped_column(
                                BigInteger, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    year:                   Mapped[str]            = mapped_column(String(4), nullable=False)
    month:                  Mapped[str]            = mapped_column(String(2), nullable=False)
    file_number:            Mapped[str]            = mapped_column(String(20), nullable=False, default="")
    response_type:          Mapped[str]            = mapped_column(String(25), nullable=False)
    return_period:          Mapped[Optional[str]]  = mapped_column(String(10))
    gen_date:               Mapped[Optional[str]]  = mapped_column(String(30))
    version:                Mapped[Optional[str]]  = mapped_column(String(20))
    checksum:               Mapped[Optional[str]]  = mapped_column(String(100))
    file_count:             Mapped[Optional[int]]  = mapped_column(Integer)
    pagination_required:    Mapped[bool]           = mapped_column(Boolean, nullable=False, default=False)
    counterparty_summary:   Mapped[Optional[dict]] = mapped_column(JSONB)
    itc_summary:            Mapped[Optional[dict]] = mapped_column(JSONB)
    b2b:                    Mapped[Optional[dict]] = mapped_column(JSONB)
    b2ba:                   Mapped[Optional[dict]] = mapped_column(JSONB)
    cdnr:                   Mapped[Optional[dict]] = mapped_column(JSONB)
    cdnra:                  Mapped[Optional[dict]] = mapped_column(JSONB)
    isd:                    Mapped[Optional[dict]] = mapped_column(JSONB)
    grand_summary:          Mapped[Optional[dict]] = mapped_column(JSONB)
    upstream_status_code:   Mapped[Optional[int]]  = mapped_column(Integer)
    fetched_at:             Mapped[datetime]        = mapped_column(TIMESTAMPTZ, nullable=False,
                                                                     server_default="NOW()")
    updated_at:             Mapped[datetime]        = mapped_column(TIMESTAMPTZ, nullable=False,
                                                                     server_default="NOW()")


# ──────────────────────────────────────────────────────────────────────
# LEDGER — representative models
# ──────────────────────────────────────────────────────────────────────

class LedgerBalance(Base):
    __tablename__ = "ledger_balance"
    __table_args__ = (
        UniqueConstraint("client_id", "year", "month", name="uq_ledger_balance"),
    )

    id:                   Mapped[int]              = mapped_column(BigInteger, primary_key=True)
    client_id:            Mapped[int]              = mapped_column(
                              BigInteger, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    year:                 Mapped[str]              = mapped_column(String(4), nullable=False)
    month:                Mapped[str]              = mapped_column(String(2), nullable=False)
    status_cd:            Mapped[Optional[str]]    = mapped_column(String(10))
    cash_igst_tax:        Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    cash_igst_total:      Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    cash_cgst_total:      Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    cash_sgst_total:      Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    cash_cess_total:      Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    itc_igst:             Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    itc_cgst:             Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    itc_sgst:             Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    itc_cess:             Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    itc_blocked_igst:     Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    itc_blocked_cgst:     Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    itc_blocked_sgst:     Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    itc_blocked_cess:     Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    upstream_status_code: Mapped[Optional[int]]     = mapped_column(Integer)
    fetched_at:           Mapped[datetime]          = mapped_column(TIMESTAMPTZ, nullable=False,
                                                                     server_default="NOW()")
    updated_at:           Mapped[datetime]          = mapped_column(TIMESTAMPTZ, nullable=False,
                                                                     server_default="NOW()")


class GstReturnStatus(Base):
    __tablename__ = "gst_return_status"
    __table_args__ = (
        UniqueConstraint("client_id", "year", "month", "reference_id",
                         name="uq_gst_return_status"),
        CheckConstraint(
            "processing_status IS NULL OR processing_status IN ('P', 'PE', 'ER', 'REC')",
            name="ck_gst_return_status_processing",
        ),
    )

    id:                      Mapped[int]            = mapped_column(BigInteger, primary_key=True)
    client_id:               Mapped[int]            = mapped_column(
                                 BigInteger, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    year:                    Mapped[str]            = mapped_column(String(4), nullable=False)
    month:                   Mapped[str]            = mapped_column(String(2), nullable=False)
    reference_id:            Mapped[str]            = mapped_column(String(100), nullable=False)
    status_cd:               Mapped[Optional[str]]  = mapped_column(String(10))
    form_type:               Mapped[Optional[str]]  = mapped_column(String(20))
    form_type_label:         Mapped[Optional[str]]  = mapped_column(String(50))
    action:                  Mapped[Optional[str]]  = mapped_column(String(20))
    processing_status:       Mapped[Optional[str]]  = mapped_column(String(10))
    processing_status_label: Mapped[Optional[str]]  = mapped_column(String(100))
    has_errors:              Mapped[Optional[bool]] = mapped_column(Boolean)
    error_report:            Mapped[Optional[dict]] = mapped_column(JSONB)
    upstream_status_code:    Mapped[Optional[int]]  = mapped_column(Integer)
    fetched_at:              Mapped[datetime]        = mapped_column(TIMESTAMPTZ, nullable=False,
                                                                      server_default="NOW()")
    updated_at:              Mapped[datetime]        = mapped_column(TIMESTAMPTZ, nullable=False,
                                                                      server_default="NOW()")
```

---

## Appendix A: Complete Table Inventory

| # | Table Name | Natural Key | Optional Filters | Strategy |
|---|-----------|-------------|-----------------|----------|
| 1 | `clients` | gstin | — | UNIQUE(gstin) |
| 2 | `client_sessions` | client_id + active | — | Partial UNIQUE WHERE active |
| 3 | `otp_requests` | — | — | Append-only audit log |
| 4 | `gstr1_advance_tax` | client_id, year, month | — | Direct UNIQUE |
| 5 | `gstr1_b2b` | client_id, year, month | action_req, from_date, counterparty | Sentinel UNIQUE |
| 6 | `gstr1_summary` | client_id, year, month, summary_type | — | Direct UNIQUE |
| 7 | `gstr1_b2csa` | client_id, year, month | — | Direct UNIQUE |
| 8 | `gstr1_b2cs` | client_id, year, month | — | Direct UNIQUE |
| 9 | `gstr1_cdnr` | client_id, year, month | action_req, from_date | Sentinel UNIQUE |
| 10 | `gstr1_doc_issue` | client_id, year, month | — | Direct UNIQUE |
| 11 | `gstr1_hsn` | client_id, year, month | — | Direct UNIQUE |
| 12 | `gstr1_nil` | client_id, year, month | — | Direct UNIQUE |
| 13 | `gstr1_b2cl` | client_id, year, month | — | Direct UNIQUE |
| 14 | `gstr1_cdnur` | client_id, year, month | — | Direct UNIQUE |
| 15 | `gstr1_exp` | client_id, year, month | — | Direct UNIQUE |
| 16 | `gstr1_txp` | client_id, year, month | counterparty, action_req, from_date | Sentinel UNIQUE |
| 17 | `gstr2a_b2b` | client_id, year, month | — | Direct UNIQUE |
| 18 | `gstr2a_b2ba` | client_id, year, month | counterparty | Sentinel UNIQUE |
| 19 | `gstr2a_cdn` | client_id, year, month | counterparty, from_date | Sentinel UNIQUE |
| 20 | `gstr2a_cdna` | client_id, year, month | counterparty | Sentinel UNIQUE |
| 21 | `gstr2a_document` | client_id, year, month | — | Direct UNIQUE |
| 22 | `gstr2a_isd` | client_id, year, month | counterparty | Sentinel UNIQUE |
| 23 | `gstr2a_tds` | client_id, year, month | — | Direct UNIQUE |
| 24 | `gstr2b` | client_id, year, month, file_number | — | Discriminator + Sentinel UNIQUE |
| 25 | `gstr2b_regen_status` | client_id, reference_id | — | Direct UNIQUE |
| 26 | `gstr3b_details` | client_id, year, month | — | Direct UNIQUE |
| 27 | `gstr3b_auto_liability` | client_id, year, month | — | Direct UNIQUE |
| 28 | `gstr9_auto_calculated` | client_id, financial_year | — | Direct UNIQUE |
| 29 | `gstr9_table8a` | client_id, financial_year, file_number | — | Sentinel UNIQUE |
| 30 | `gstr9_details` | client_id, financial_year | — | Direct UNIQUE |
| 31 | `ledger_balance` | client_id, year, month | — | Direct UNIQUE |
| 32 | `ledger_cash` | client_id, from_date, to_date | — | Direct UNIQUE |
| 33 | `ledger_itc` | client_id, from_date, to_date | — | Direct UNIQUE |
| 34 | `ledger_liability` | client_id, year, month, from_date, to_date | — | Direct UNIQUE |
| 35 | `gst_return_status` | client_id, year, month, reference_id | — | Direct UNIQUE |

**Total: 35 tables | 0 hash columns | 0 NULL keys | 100% schema-enforced idempotency**