# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered e-invoice processing platform that ingests UBL 2.1 XML invoices, stores normalized data in PostgreSQL, detects anomalies via deterministic rules, and lets users generate compliance/business reports using natural language.

**Stack:** Python 3.11 + FastAPI + SQLAlchemy (async) + PostgreSQL | Next.js 14 + Tailwind + Recharts | OpenAI API

---

## Running the Project

### Docker (recommended)
```bash
cp .env.example .env   # add OPENAI_API_KEY
docker compose up --build
```
- Frontend: http://localhost:3000
- Backend API + docs: http://localhost:8000 / http://localhost:8000/docs
- Mock Peppol provider: http://localhost:8001

### Without Docker

**Backend:**
```bash
createdb einvoicing
cd backend
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
# Copy backend/.env.example to backend/.env and fill in values
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Mock provider (separate terminal):**
```bash
cd mock-provider
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**Frontend (separate terminal):**
```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

### Environment Variables (backend)
| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/einvoicing` | Async asyncpg driver required |
| `OPENAI_API_KEY` | — | Required for AI features; system falls back to keyword templates if absent |
| `OPENAI_MODEL` | `gpt-4o-mini` | |
| `MOCK_PROVIDER_URL` | `http://localhost:8001` | |
| `EINVOICE_BE_API_KEY` | — | e-invoice.be Peppol Access Point API key |
| `EINVOICE_BE_ENV` | `staging` | `staging` or `production` |

---

## Architecture

### Data Flow

```
XML Invoice (upload / email / Peppol provider)
  → ingestion.ingest_xml()          # deduplication by SHA-256 hash
  → ubl_parser.parse_ubl()          # lxml → normalized dict
  → DB: RawInvoiceFile + Party + Invoice + InvoiceLine + TaxSubtotal
  → anomaly_service.run_deterministic_checks()   # runs immediately on import

User NL prompt  → POST /reports/generate
  → ai_service.generate_report_definition()      # OpenAI → ReportDefinition JSON
  → schemas/report.py ReportDefinition (Pydantic validation + allowlist)
  → report_engine.compile_to_sql()               # safe parameterised SQL
  → report_validator pipeline (EXPLAIN + completeness + reconciliation + quality score)
  → ai_service.explain_report()                  # OpenAI narrative
  → DB: ReportRun persisted
```

### Backend (`backend/app/`)

| Path | Role |
|---|---|
| `main.py` | FastAPI app wiring, CORS, startup table creation |
| `config.py` | `Settings` via pydantic-settings; reads `.env` |
| `database.py` | Async SQLAlchemy engine + session factory |
| `models/models.py` | All ORM models: `RawInvoiceFile`, `Party`, `Invoice`, `InvoiceLine`, `TaxSubtotal`, `ReportRun`, `Anomaly`, `AuditLog` |
| `schemas/report.py` | `ALLOWED_FIELDS` allowlist + `ReportDefinition` Pydantic model — the security boundary for SQL generation |
| `schemas/invoice.py` | Invoice request/response schemas |
| `services/ubl_parser.py` | lxml-based UBL 2.1 / Peppol BIS XML parser |
| `services/ingestion.py` | Full import pipeline with dedup + party upsert |
| `services/anomaly_service.py` | 10 deterministic rule checks (dup invoice numbers, VAT mismatches, date logic, etc.) |
| `services/ai_service.py` | OpenAI calls: report definition generation, result narration, spend classification, anomaly explanation |
| `services/report_engine.py` | Compiles `ReportDefinition` → parameterised SQL + executes it |
| `services/report_validator.py` | Multi-step validation: EXPLAIN SQL, dataset completeness, reconciliation, data quality score |
| `services/belgian_vat_return.py` | Calculates Intervat grid values + generates Belgian VAT XML |
| `services/einvoice_be.py` | e-invoice.be API client: inbox fetch, UBL download, outgoing send (two-step create+send), `build_json_payload()` |
| `services/ubl_builder.py` | Builds Peppol BIS Billing 3.0 / UBL 2.1 XML from structured dict for local storage |
| `routers/invoices.py` | Upload, list, detail, provider fetch, anomaly detection, outgoing send endpoints |
| `routers/reports.py` | NL report generation, list, detail, drilldown, Belgian VAT return |
| `routers/anomalies.py` | Anomaly listing |
| `routers/dashboard.py` | Dashboard stats |
| `routers/audit.py` | Audit log listing |

### Report Generation Security Model

The LLM produces a `ReportDefinition` JSON. Before any SQL runs:
1. `ReportDefinition` Pydantic model validates every field against `ALLOWED_FIELDS` (whitelist in `schemas/report.py`).
2. `report_engine.compile_to_sql()` uses only allowlisted column names and SQLAlchemy `text()` with named parameters — no raw string interpolation of user values.
3. `validate_sql()` runs `EXPLAIN` on the compiled SQL before execution.

When adding new queryable fields, update `ALLOWED_FIELDS` in `schemas/report.py` **and** the `REPORT_SYSTEM_PROMPT` in `ai_service.py`.

### Database Schema (key relationships)

```
RawInvoiceFile (1) → (*) Invoice
Party (supplier/customer) ← Invoice → InvoiceLine, TaxSubtotal
Invoice → Anomaly, AuditLog (indirect via entity_id)
ReportRun (standalone, stores JSON result + SQL)
```

No Alembic migrations exist — `Base.metadata.create_all` runs on startup. Adding columns to existing tables requires manual `ALTER TABLE`.

### Outgoing Invoice Flow (Send via Peppol)

`POST /invoices/send` → `ubl_builder.build_ubl_invoice()` (stores as UBL XML in DB) + `einvoice_be.send_outbox_invoice()` (Peppol delivery).

The e-invoice.be delivery uses a **two-step** workflow:
1. `POST /api/documents/` — create document using `DocumentCreate` JSON schema
2. `POST /api/documents/{id}/send` — deliver via Peppol

The payload mapping (our form → e-invoice.be fields) lives in `einvoice_be.build_json_payload()`.

---

## e-invoice.be API Reference

Full spec: [`docs/api-1.json`](docs/api-1.json) (OpenAPI 3.1.0 v1.1.0)

**Base URLs:** staging `https://api-dev.e-invoice.be` · production `https://api.e-invoice.be`  
**Auth:** `Authorization: Bearer <EINVOICE_BE_API_KEY>` on all endpoints except the public lookup endpoints.

### Key Endpoints

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/me/` | Verify API key / account info |
| `POST` | `/api/documents/` | Create invoice/credit note (JSON body, see schema below) |
| `POST` | `/api/documents/{id}/send` | Send created document via Peppol. Query params: `sender_peppol_scheme`, `sender_peppol_id`, `receiver_peppol_scheme`, `receiver_peppol_id` (all optional) |
| `POST` | `/api/documents/{id}/validate` | Validate against Peppol BIS Billing 3.0 |
| `GET` | `/api/documents/{id}` | Get document details |
| `GET` | `/api/documents/{id}/ubl` | Download raw UBL XML |
| `POST` | `/api/documents/ubl` | Create document from UBL XML file (multipart, field `file`) |
| `POST` | `/api/documents/pdf` | Create document from PDF (multipart) |
| `GET` | `/api/inbox/` | List received documents (paginated, filter by type/sender/date/search) |
| `GET` | `/api/inbox/invoices` | List received invoices (simpler, no type filter) |
| `GET` | `/api/outbox/` | List sent documents |
| `POST` | `/api/validate/json` | Validate JSON without creating a document |
| `POST` | `/api/validate/ubl` | Validate UBL XML file (multipart) |
| `GET` | `/api/validate/peppol-id` | Check if a Peppol ID is registered (requires auth). Query param: `peppol_id` e.g. `0208:1018265814` |
| `GET` | `/api/lookup` | Detailed Peppol ID diagnostic — DNS, SMP, certs (no auth) |
| `GET` | `/api/lookup/participants` | Search participants by name/identifier (no auth). Query: `query`, `country_code` |
| `GET` | `/api/stats` | Usage statistics. Query: `start_date`, `end_date`, `aggregation` (DAY/WEEK/MONTH) |
| `GET/POST/PUT/DELETE` | `/api/webhooks/` | Webhook CRUD |

### DocumentCreate JSON Schema (POST /api/documents/)

No fields are server-required except `items` (minItems: 1). Peppol BIS 3.0 validation will reject missing mandatory fields on send.

| Field | Type | Notes |
|---|---|---|
| `document_type` | enum | `INVOICE` (default), `CREDIT_NOTE`, `DEBIT_NOTE` |
| `invoice_id` | string | Invoice number |
| `invoice_date` | date string | ISO 8601 |
| `due_date` | date string | |
| `currency` | string | ISO 4217, default `EUR` |
| `vendor_name` | string | Supplier company name |
| `vendor_tax_id` | string | VAT number with country prefix e.g. `BE1018265814`, `SI52044971` |
| `vendor_email` | string | |
| `customer_name` | string | Buyer company name |
| `customer_tax_id` | string | VAT number with country prefix |
| `customer_peppol_id` | string | Peppol endpoint e.g. `0208:0848934496` — used for routing |
| `customer_email` | string | |
| `purchase_order` | string | Buyer PO reference (maps from `buyer_reference`) |
| `payment_term` | string | e.g. `Net 30` |
| `payment_details` | array | `[{iban, swift, bank_account_number, payment_reference}]` |
| `note` | string | Free text |
| `tax_code` | enum | `S` (standard), `Z` (zero), `E` (exempt), `AE` (reverse charge), `K` (intra-EU) |
| `items` | array | Line items — see below |

**Line item fields (`items[]`):**

| Field | Type | Notes |
|---|---|---|
| `description` | string | |
| `quantity` | number | Max 4 decimals |
| `unit_price` | number | Net price excl. VAT, max 4 decimals |
| `tax_rate` | string | e.g. `"21.00"`, `"6.00"` |
| `amount` | number | Net line amount excl. VAT (optional, computed if omitted) |
| `unit` | string | UN/CEFACT unit code |

### Peppol ID Format

Belgian companies: `0208:` + 10-digit KBO/BTW number (without `BE` prefix). E.g. `BE0848934496` → `0208:0848934496`.

Other countries use different scheme codes. Always verify with `GET /api/lookup?peppol_id=<id>` before sending.

### Webhook Events

Create webhooks via `POST /api/webhooks/` with `{url, events: [...], enabled: true}`. Test with `POST /api/webhooks/{id}/test`.

### Mock Peppol Provider

`mock-provider/main.py` serves `GET /provider/invoices` returning JSON `{"invoices": [{filename, xml_content}]}` from XML files in `mock-provider/invoices/`. Sample invoices also live in `sample-invoices/` (25 UBL XMLs covering Q4 2025 + Q1 2026, 6 suppliers, all anomaly types).

### Frontend (`frontend/`)

Next.js 14 App Router. Pages in `app/`, reusable components in `components/`. API calls use `NEXT_PUBLIC_API_URL` env var. Key pages: dashboard, invoices list/detail, upload, reports (NL chat interface), anomalies, settings. No frontend state management library — local React state only.

---

## Key Conventions

- All DB access is async (`AsyncSession`, `await db.execute()`).
- `Party` records are upserted by `vat_id`; parties without a VAT ID always get a new row.
- Anomaly detection runs automatically inside `ingest_xml()` after each successful import (no separate trigger needed).
- `ai_service.py` functions silently fall back to keyword templates or canned strings when `OPENAI_API_KEY` is not set or the API call fails.
- The `X-User-Id` request header is used as the `actor` field in `ReportRun` and `AuditLog`; defaults to `"anonymous"`.
