"""
AI service: OpenAI-backed helpers for report generation, spend classification,
anomaly explanation, and report result narration.

Falls back to predefined templates when the OpenAI call fails or returns
invalid JSON.
"""
from __future__ import annotations

import json
import re
from typing import Any

from openai import AsyncOpenAI

from app.config import settings

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# System prompt for report generation
# ---------------------------------------------------------------------------

REPORT_SYSTEM_PROMPT = """\
You are an E-Invoicing analytics assistant. Your task is to translate natural language
business questions into a structured JSON "report definition" that a deterministic SQL
compiler will execute against a UBL invoice database.

## Database schema overview

Tables:
- invoices: id, invoice_number, invoice_type, direction, issue_date, due_date,
            currency, supplier_id, customer_id, payable_amount, tax_amount,
            tax_exclusive_amount, tax_inclusive_amount, created_at
- parties (aliased as supplier or customer): id, name, vat_id, country_code, endpoint_id, iban
- invoice_lines: id, invoice_id, line_number, description, quantity, unit_price,
                 line_amount, tax_category, tax_percent
- tax_subtotals: id, invoice_id, tax_category, tax_percent, taxable_amount, tax_amount

## Allowed field references (use EXACTLY these names)

Invoice fields:
  invoice.issue_date, invoice.due_date, invoice.currency, invoice.direction,
  invoice.payable_amount, invoice.invoice_number

Supplier fields:
  supplier.name, supplier.vat_id, supplier.country_code

Customer fields:
  customer.name, customer.vat_id

Tax subtotal fields:
  tax_subtotals.tax_category, tax_subtotals.tax_percent,
  tax_subtotals.taxable_amount, tax_subtotals.tax_amount

Invoice line fields:
  invoice_lines.description, invoice_lines.line_amount,
  invoice_lines.tax_category, invoice_lines.tax_percent

## Report Definition JSON Schema

{
  "reportName": "<string — concise human-readable name>",
  "entity": "<one of: invoices | tax_subtotals | invoice_lines>",
  "filters": [
    {
      "field": "<allowed field>",
      "operator": "<eq | neq | gt | gte | lt | lte | between | in | like>",
      "value": <scalar, list for 'in', [lo, hi] for 'between'>
    }
  ],
  "groupBy": ["<allowed field>", ...],
  "metrics": [
    {
      "field": "<allowed field or * for count>",
      "aggregation": "<sum | count | avg | min | max>",
      "alias": "<snake_case alias>"
    }
  ],
  "orderBy": [
    { "field": "<alias or allowed field>", "direction": "<asc | desc>" }
  ],
  "limit": 1000
}

## Rules
1. Always include at least one metric.
2. Every field in groupBy must also appear in the SELECT (handled automatically).
3. Use parameterised operators — never embed raw user values into field names.
4. For VAT / tax reports use entity="tax_subtotals".
5. For line-level spend use entity="invoice_lines".
6. For invoice-level totals use entity="invoices".
7. Dates use ISO 8601 format (YYYY-MM-DD) in filter values.

## Example 1 — VAT collected by rate

{
  "reportName": "VAT by Tax Rate",
  "entity": "tax_subtotals",
  "filters": [],
  "groupBy": ["tax_subtotals.tax_percent"],
  "metrics": [
    {"field": "tax_subtotals.taxable_amount", "aggregation": "sum", "alias": "total_taxable"},
    {"field": "tax_subtotals.tax_amount",     "aggregation": "sum", "alias": "total_vat"}
  ],
  "orderBy": [{"field": "tax_subtotals.tax_percent", "direction": "asc"}],
  "limit": 100
}

## Example 2 — Top suppliers by spend

{
  "reportName": "Top Suppliers by Spend",
  "entity": "invoices",
  "filters": [],
  "groupBy": ["supplier.name", "supplier.vat_id"],
  "metrics": [
    {"field": "invoice.payable_amount", "aggregation": "sum",   "alias": "total_spend"},
    {"field": "*",                       "aggregation": "count", "alias": "invoice_count"}
  ],
  "orderBy": [{"field": "total_spend", "direction": "desc"}],
  "limit": 50
}

## Example 3 — Monthly invoice volume

{
  "reportName": "Monthly Invoice Volume",
  "entity": "invoices",
  "filters": [],
  "groupBy": ["invoice.currency"],
  "metrics": [
    {"field": "*",                        "aggregation": "count", "alias": "invoice_count"},
    {"field": "invoice.payable_amount",   "aggregation": "sum",   "alias": "total_amount"},
    {"field": "invoice.tax_amount",       "aggregation": "sum",   "alias": "total_vat"}
  ],
  "orderBy": [{"field": "total_amount", "direction": "desc"}],
  "limit": 100
}

## Output instructions
Respond with ONLY the JSON object — no markdown fences, no explanation, no preamble.
The JSON must be valid and match the schema exactly.
"""


# ---------------------------------------------------------------------------
# Predefined fallback templates
# ---------------------------------------------------------------------------

_FALLBACK_TEMPLATES: list[dict[str, Any]] = [
    {
        "keywords": ["vat by rate", "vat rate", "tax rate", "vat breakdown"],
        "definition": {
            "reportName": "VAT by Tax Rate",
            "entity": "tax_subtotals",
            "filters": [],
            "groupBy": ["tax_subtotals.tax_percent"],
            "metrics": [
                {"field": "tax_subtotals.taxable_amount", "aggregation": "sum", "alias": "total_taxable"},
                {"field": "tax_subtotals.tax_amount", "aggregation": "sum", "alias": "total_vat"},
            ],
            "orderBy": [{"field": "tax_subtotals.tax_percent", "direction": "asc"}],
            "limit": 100,
        },
    },
    {
        "keywords": ["vat by supplier", "supplier vat", "tax by supplier"],
        "definition": {
            "reportName": "VAT by Supplier",
            "entity": "tax_subtotals",
            "filters": [],
            "groupBy": ["supplier.name", "supplier.vat_id"],
            "metrics": [
                {"field": "tax_subtotals.taxable_amount", "aggregation": "sum", "alias": "total_taxable"},
                {"field": "tax_subtotals.tax_amount", "aggregation": "sum", "alias": "total_vat"},
                {"field": "*", "aggregation": "count", "alias": "invoice_count"},
            ],
            "orderBy": [{"field": "total_vat", "direction": "desc"}],
            "limit": 100,
        },
    },
    {
        "keywords": ["spend by supplier", "top supplier", "supplier spend", "spending by supplier"],
        "definition": {
            "reportName": "Spend by Supplier",
            "entity": "invoices",
            "filters": [],
            "groupBy": ["supplier.name", "supplier.vat_id"],
            "metrics": [
                {"field": "invoice.payable_amount", "aggregation": "sum", "alias": "total_spend"},
                {"field": "*", "aggregation": "count", "alias": "invoice_count"},
            ],
            "orderBy": [{"field": "total_spend", "direction": "desc"}],
            "limit": 50,
        },
    },
]


def _fallback_template(prompt: str) -> dict[str, Any] | None:
    lower = prompt.lower()
    for template in _FALLBACK_TEMPLATES:
        if any(kw in lower for kw in template["keywords"]):
            return template["definition"]
    # Default fallback: invoice summary
    return {
        "reportName": "Invoice Summary",
        "entity": "invoices",
        "filters": [],
        "groupBy": ["invoice.currency"],
        "metrics": [
            {"field": "*", "aggregation": "count", "alias": "invoice_count"},
            {"field": "invoice.payable_amount", "aggregation": "sum", "alias": "total_amount"},
            {"field": "invoice.tax_amount", "aggregation": "sum", "alias": "total_vat"},
        ],
        "orderBy": [{"field": "total_amount", "direction": "desc"}],
        "limit": 100,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def generate_report_definition(prompt: str) -> dict[str, Any]:
    """
    Call the LLM to generate a ReportDefinition JSON.
    Falls back to template matching on any failure.
    """
    if not settings.OPENAI_API_KEY:
        return _fallback_template(prompt)

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or ""
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw.strip())
        return json.loads(raw)
    except Exception:
        return _fallback_template(prompt)


async def explain_report(
    prompt: str,
    report_def: dict[str, Any],
    rows: list[dict[str, Any]],
    row_count: int,
) -> str:
    """
    Generate a plain-English narrative explaining the report results.
    Falls back to a minimal canned response on failure.
    """
    if not settings.OPENAI_API_KEY:
        return (
            f"The report '{report_def.get('reportName', 'Report')}' returned {row_count} row(s). "
            "Please review the data above for details."
        )

    sample = rows[:10]
    system = (
        "You are a helpful financial analyst. Given a report definition, the user's original "
        "question, and the first few rows of results, write 2-3 concise paragraphs explaining "
        "what the data shows. Focus on business insights — totals, trends, outliers. "
        "Do not mention SQL or technical implementation details."
    )
    user_msg = (
        f"User question: {prompt}\n\n"
        f"Report name: {report_def.get('reportName')}\n"
        f"Total rows returned: {row_count}\n"
        f"Sample rows (first 10):\n{json.dumps(sample, indent=2)}"
    )

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.4,
            max_tokens=512,
        )
        return response.choices[0].message.content or ""
    except Exception:
        return (
            f"The report '{report_def.get('reportName', 'Report')}' returned {row_count} row(s). "
            "Please review the data above for details."
        )


async def classify_spend_category(description: str) -> str:
    """
    Classify an invoice line description into a spend category.
    Returns one of: software, consulting, office_supplies, travel,
                    telecom, marketing, legal, other
    """
    categories = [
        "software", "consulting", "office_supplies", "travel",
        "telecom", "marketing", "legal", "other",
    ]

    if not settings.OPENAI_API_KEY:
        return "other"

    system = (
        "You are a spend classification assistant. Given an invoice line description, "
        "respond with exactly one word from this list: "
        + ", ".join(categories)
        + ". No explanation."
    )

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": description},
            ],
            temperature=0,
            max_tokens=10,
        )
        answer = (response.choices[0].message.content or "other").strip().lower()
        return answer if answer in categories else "other"
    except Exception:
        return "other"


async def explain_anomaly(anomaly: dict[str, Any], invoice: dict[str, Any]) -> str:
    """
    Generate a brief explanation of why an anomaly is suspicious.
    """
    if not settings.OPENAI_API_KEY:
        return anomaly.get("message", "Anomaly detected.")

    system = (
        "You are an e-invoicing compliance expert. Given an anomaly and the invoice context, "
        "write 1-2 sentences explaining why this is suspicious and what action should be taken. "
        "Be concise and actionable."
    )
    user_msg = (
        f"Anomaly category: {anomaly.get('category')}\n"
        f"Severity: {anomaly.get('severity')}\n"
        f"Message: {anomaly.get('message')}\n"
        f"Invoice number: {invoice.get('invoice_number')}\n"
        f"Supplier: {invoice.get('supplier_name')}\n"
        f"Amount: {invoice.get('payable_amount')} {invoice.get('currency')}"
    )

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=128,
        )
        return response.choices[0].message.content or anomaly.get("message", "")
    except Exception:
        return anomaly.get("message", "Anomaly detected.")
