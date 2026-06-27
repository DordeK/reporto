# E-Invoicing AI Processor

An AI-powered e-invoice processing platform that ingests UBL 2.1 XML invoices from a mock Peppol network provider, parses and stores them in a structured database, detects anomalies using LLM-based reasoning, and presents the results in an interactive dashboard. Built as a hackathon proof-of-concept demonstrating how AI can automate and audit the accounts-payable workflow end-to-end.

---

## Quick Start with Docker Compose

**Prerequisites:** Docker Desktop installed and running, an OpenAI API key.

1. Copy the environment file and add your key:
   ```bash
   cp .env.example .env
   # Edit .env and set OPENAI_API_KEY=sk-...
   ```

2. Build and start all services:
   ```bash
   docker compose up --build
   ```

3. Open the frontend at [http://localhost:3000](http://localhost:3000). The backend API is at [http://localhost:8000](http://localhost:8000) and the mock Peppol provider at [http://localhost:8001](http://localhost:8001).

---

## Quick Start without Docker

### Backend (FastAPI + PostgreSQL)

**Prerequisites:** Python 3.11+, PostgreSQL 16 running locally.

1. Create the database:
   ```bash
   createdb einvoicing
   ```

2. Install dependencies and run:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Set environment variables:
   ```bash
   export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/einvoicing
   export OPENAI_API_KEY=sk-...
   export OPENAI_MODEL=gpt-4o-mini
   ```

4. Start the backend:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Mock Provider (separate terminal)

```bash
cd mock-provider
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend (Next.js)

**Prerequisites:** Node.js 20+.

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key (used by the backend for LLM-based anomaly detection) | Yes |
| `OPENAI_MODEL` | Model to use (default: `gpt-4o-mini`) | No |
| `DATABASE_URL` | PostgreSQL async connection string | Yes (set automatically in Docker) |

---

## Demo Flow

1. **Start the stack** — `docker compose up --build` brings up Postgres, backend, mock provider, and frontend.
2. **Open the dashboard** — Navigate to [http://localhost:3000](http://localhost:3000). The invoice list is initially empty.
3. **Fetch invoices from the provider** — Click "Fetch from Provider". The backend calls `GET /provider/invoices` on the mock provider (port 8001), which returns 10 UBL XML invoices as JSON.
4. **Parse and store** — The backend parses each XML file, extracts structured fields (invoice ID, supplier, customer, dates, line items, VAT details), and persists them to PostgreSQL.
5. **View the invoice list** — The dashboard populates with all fetched invoices showing supplier, amount, VAT, issue date, and status.
6. **Inspect a single invoice** — Click any row to see the full parsed detail view including all line items and tax subtotals.
7. **Run AI anomaly detection** — Click "Detect Anomalies" to send all stored invoices to the LLM. The model checks for: duplicate invoice numbers from the same supplier, VAT calculation mismatches, due dates before issue dates, missing supplier VAT IDs, and reverse-charge invoices with non-zero tax amounts.
8. **Review anomaly report** — The UI displays each flagged invoice with the anomaly type, a plain-language explanation from the LLM, and a severity rating.
9. **Filter by supplier or category** — Use the filter controls to narrow the invoice list by supplier name or spend category.
10. **Explore the full sample set** — The `sample-invoices/` directory contains all 25 UBL XML invoices including Q4 2025 and Q1 2026 invoices across 6 suppliers with all anomaly types embedded.

---

## API Documentation

The backend exposes a FastAPI app. Interactive docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/invoices` | List all stored invoices (paginated) |
| `GET` | `/invoices/{id}` | Get a single invoice with full line items |
| `POST` | `/invoices/fetch` | Fetch and ingest invoices from the mock provider |
| `POST` | `/invoices/detect-anomalies` | Run LLM anomaly detection on all stored invoices |
| `GET` | `/invoices/anomalies` | List all previously detected anomalies |
| `GET` | `/health` | Health check |

---

## Hackathon Pitch

Every company receives hundreds of supplier invoices per month. Today, accounts-payable teams manually verify VAT calculations, chase down missing registration numbers, and hunt for duplicates — work that is tedious, error-prone, and adds no value.

This project shows that the entire intake-to-audit pipeline can be automated with a small AI layer on top of standard e-invoicing infrastructure. We ingest structured UBL 2.1 XML invoices exactly as they would arrive over the Peppol network, parse them into a queryable database, and then ask a language model to act as a senior AP auditor: find the duplicates, flag the VAT mismatches, catch the impossible due dates, and explain each finding in plain language.

The result is a dashboard where a finance team can review AI-flagged exceptions in minutes instead of hours, approve clean invoices in bulk, and have a full audit trail — all without writing a single validation rule by hand. As e-invoicing mandates roll out across the EU, this pattern becomes the natural foundation for any compliant AP automation stack.
