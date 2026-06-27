"""
AI service: OpenAI-backed helpers for report generation, spend classification,
anomaly explanation, and report result narration.

Falls back to predefined templates when the OpenAI call fails or returns
invalid JSON.
"""
from __future__ import annotations

import json
import re
from datetime import date
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
You are an E-Invoicing analytics assistant. Translate natural language business questions
into a structured JSON "report definition" that a deterministic SQL compiler will execute
against a UBL 2.1 / Peppol BIS Billing 3.0 invoice database.

The schema is fully aligned with the UBL 2.1 OASIS standard
(https://docs.oasis-open.org/ubl/UBL-2.1.html). Every column maps to a UBL Business Term (BT).

=== ALLOWED FIELD REFERENCES (use EXACTLY these dot-notation names) ===

INVOICE HEADER  (entity="invoices")
  invoice.invoice_number              BT-1   Unique invoice identifier
  invoice.invoice_type                BT-3   380=Invoice 381=CreditNote 389=SelfBilling
  invoice.issue_date                  BT-2   Invoice issue date (YYYY-MM-DD)
  invoice.due_date                    BT-9   Payment due date
  invoice.tax_point_date              BT-7   Date of supply / tax point
  invoice.currency                    BT-5   Invoice currency (ISO 4217, e.g. EUR)
  invoice.tax_currency_code           BT-6   VAT accounting currency
  invoice.direction                   -      "received" or "sent"
  invoice.note                        BT-22  Free-text note
  invoice.buyer_reference             BT-10  Buyer internal reference / cost centre
  invoice.accounting_cost             BT-19  Buyer accounting / booking reference
  invoice.customization_id            BT-24  Peppol specification identifier
  invoice.profile_id                  BT-23  Business process identifier
  invoice.invoice_period_start        BT-73  Service/delivery period start
  invoice.invoice_period_end          BT-74  Service/delivery period end
  invoice.order_reference_id          BT-13  Purchase order reference
  invoice.sales_order_id              BT-14  Sales order reference
  invoice.contract_document_reference_id  BT-12  Contract reference
  invoice.billing_reference_id        BT-25  Preceding invoice ref (credit notes)
  invoice.project_reference_id        BT-11  Project reference
  invoice.despatch_document_reference_id  BT-16  Despatch advice reference
  invoice.receipt_document_reference_id   BT-15  Receiving advice reference
  invoice.payment_means_code          BT-81  Payment means (30=credit-xfer 49=direct-debit 58=SEPA)
  invoice.payment_terms_note          BT-20  Payment terms text
  invoice.line_extension_amount       BT-106 Sum of line net amounts
  invoice.allowance_total_amount      BT-107 Sum of doc-level allowances
  invoice.charge_total_amount         BT-108 Sum of doc-level charges
  invoice.tax_exclusive_amount        BT-109 Invoice total excl. VAT
  invoice.tax_amount                  BT-110 Invoice total VAT amount
  invoice.tax_inclusive_amount        BT-112 Invoice total incl. VAT
  invoice.prepaid_amount              BT-113 Already paid amount
  invoice.payable_amount              BT-115 Amount due for payment
  invoice.delivery_actual_delivery_date  BT-72  Actual delivery date
  invoice.delivery_country_code       BT-80  Deliver-to country
  invoice.delivery_city_name          -      Deliver-to city
  invoice.peppol_state                -      DRAFT|TRANSIT|FAILED|SENT|RECEIVED

SELLER/SUPPLIER  (BG-4)
  supplier.name                       BT-27  Seller trading name
  supplier.vat_id                     BT-31  Seller VAT identifier
  supplier.country_code               BT-40  Seller country (ISO 3166-1 alpha-2)
  supplier.city_name                  BT-37  Seller city
  supplier.postal_zone                BT-38  Seller postcode
  supplier.registration_name          BT-28  Seller legal registration name
  supplier.company_id                 BT-47  Seller CBE/KBO number
  supplier.endpoint_id                BT-34  Seller Peppol electronic address
  supplier.endpoint_scheme            -      Seller endpoint scheme (e.g. 0208 for Belgium)

BUYER/CUSTOMER  (BG-7)
  customer.name                       BT-44  Buyer name
  customer.vat_id                     BT-48  Buyer VAT identifier
  customer.country_code               BT-55  Buyer country
  customer.city_name                  BT-52  Buyer city
  customer.registration_name          BT-45  Buyer legal registration name
  customer.company_id                 BT-47  Buyer CBE/KBO number

TAX SUBTOTALS  (BG-23)  — use entity="tax_subtotals"
  tax_subtotals.tax_category              BT-118  S=standard Z=zero E=exempt K=IC AE=reverse-charge
  tax_subtotals.tax_percent               BT-119  VAT rate (21, 12, 6, 0, …)
  tax_subtotals.taxable_amount            BT-116  Taxable amount per VAT category
  tax_subtotals.tax_amount                BT-117  VAT amount per category
  tax_subtotals.tax_exemption_reason_code BT-121  VATEX-* exemption code

INVOICE LINES  (BG-25)  — use entity="invoice_lines"
  invoice_lines.description              BT-154  Item description
  invoice_lines.item_name                BT-153  Item name
  invoice_lines.quantity                 BT-129  Invoiced quantity
  invoice_lines.unit_price               BT-146  Item net price (excl. VAT)
  invoice_lines.line_amount              BT-131  Line net amount
  invoice_lines.tax_category             BT-151  Line VAT category
  invoice_lines.tax_percent              BT-152  Line VAT rate
  invoice_lines.accounting_cost          BT-133  Line buyer accounting reference
  invoice_lines.sellers_item_id          BT-155  Seller item identifier
  invoice_lines.buyers_item_id           BT-156  Buyer item identifier
  invoice_lines.standard_item_id         BT-157  Standard identifier (GTIN/EAN)
  invoice_lines.commodity_classification_code  BT-158  CPV / UNSPSC commodity code
  invoice_lines.item_origin_country      BT-159  Item country of origin
  invoice_lines.tax_exemption_reason_code  -     Line exemption reason code

=== REPORT DEFINITION JSON SCHEMA ===

{
  "reportName": "<string>",
  "entity": "<invoices | tax_subtotals | invoice_lines>",
  "filters": [{"field": "<field>", "operator": "<eq|neq|gt|gte|lt|lte|between|in|like>", "value": <scalar|list>}],
  "groupBy": ["<field>", ...],
  "metrics": [{"field": "<field or *>", "aggregation": "<sum|count|avg|min|max>", "alias": "<snake_case>"}],
  "orderBy": [{"field": "<alias or field>", "direction": "<asc|desc>"}],
  "limit": 1000
}

=== RULES ===
1. Always include at least one metric.
2. Every groupBy field is automatically added to SELECT.
3. Never embed raw user values into field names — use parameterised operators.
4. VAT / tax analysis → entity="tax_subtotals".
5. Line-level / item analysis → entity="invoice_lines".
6. Invoice-level / header analysis → entity="invoices".
7. Dates: ISO 8601 (YYYY-MM-DD) in filter values.
8. Synonym mapping — recognise these common UBL terms:
   "net amount"/"excl. VAT"/"taxable base" → invoice.tax_exclusive_amount or invoice_lines.line_amount
   "gross amount"/"incl. VAT"              → invoice.tax_inclusive_amount
   "amount due"/"payable"                  → invoice.payable_amount
   "VAT amount"/"tax collected"            → invoice.tax_amount or tax_subtotals.tax_amount
   "invoice date"/"issue date"             → invoice.issue_date
   "supply date"/"tax point"               → invoice.tax_point_date
   "credit note"/"credit memo"             → filter invoice.invoice_type eq "381"
   "self-billing"                          → filter invoice.invoice_type eq "389"
   "SEPA credit transfer"                  → filter invoice.payment_means_code eq "30"
   "direct debit"                          → filter invoice.payment_means_code eq "49"
   "exempt"/"zero-rated"/"IC supply"       → filter tax_subtotals.tax_category in ["E","Z","K"]
   "reverse charge"                        → filter tax_subtotals.tax_category eq "AE"
   "seller"/"vendor"                       → supplier.* fields
   "buyer"/"purchaser"/"client"            → customer.* fields
   "CPV"/"commodity code"/"UNSPSC"         → invoice_lines.commodity_classification_code
   "GTIN"/"EAN"/"standard item"            → invoice_lines.standard_item_id
   "Peppol status"/"network state"         → invoice.peppol_state
   "Belgian endpoint"/"scheme 0208"        → supplier.endpoint_scheme eq "0208"
   "BT-N" references                       → use the corresponding field listed above
9. IMPORTANT: If the input is NOT a report/data question (greetings, random text, off-topic),
   respond with ONLY: {"not_a_report": true, "message": "Please ask a business question about your invoices, VAT, or spending. For example: 'Show VAT by supplier for Q1' or 'Find anomalies in received invoices'."}

=== EXAMPLES ===

## VAT by rate and category (BG-23)
{"reportName":"VAT by Rate and Category","entity":"tax_subtotals","filters":[],"groupBy":["tax_subtotals.tax_percent","tax_subtotals.tax_category"],"metrics":[{"field":"tax_subtotals.taxable_amount","aggregation":"sum","alias":"total_taxable"},{"field":"tax_subtotals.tax_amount","aggregation":"sum","alias":"total_vat"},{"field":"*","aggregation":"count","alias":"line_count"}],"orderBy":[{"field":"tax_subtotals.tax_percent","direction":"asc"}],"limit":100}

## Top suppliers by spend (BT-27, BT-115)
{"reportName":"Top Suppliers by Spend","entity":"invoices","filters":[],"groupBy":["supplier.name","supplier.vat_id","supplier.country_code"],"metrics":[{"field":"invoice.payable_amount","aggregation":"sum","alias":"total_spend"},{"field":"invoice.tax_exclusive_amount","aggregation":"sum","alias":"total_net"},{"field":"*","aggregation":"count","alias":"invoice_count"}],"orderBy":[{"field":"total_spend","direction":"desc"}],"limit":50}

## Credit notes by supplier (BT-3=381)
{"reportName":"Credit Notes by Supplier","entity":"invoices","filters":[{"field":"invoice.invoice_type","operator":"eq","value":"381"}],"groupBy":["supplier.name","supplier.vat_id"],"metrics":[{"field":"invoice.payable_amount","aggregation":"sum","alias":"total_credited"},{"field":"*","aggregation":"count","alias":"credit_note_count"}],"orderBy":[{"field":"total_credited","direction":"desc"}],"limit":100}

## Spend by CPV commodity code (BT-158)
{"reportName":"Spend by Commodity Code","entity":"invoice_lines","filters":[],"groupBy":["invoice_lines.commodity_classification_code"],"metrics":[{"field":"invoice_lines.line_amount","aggregation":"sum","alias":"total_spend"},{"field":"*","aggregation":"count","alias":"line_count"}],"orderBy":[{"field":"total_spend","direction":"desc"}],"limit":100}

## Q1 invoices by payment method (BT-81)
{"reportName":"Q1 Invoices by Payment Method","entity":"invoices","filters":[{"field":"invoice.issue_date","operator":"between","value":["2025-01-01","2025-03-31"]}],"groupBy":["invoice.payment_means_code"],"metrics":[{"field":"invoice.payable_amount","aggregation":"sum","alias":"total_amount"},{"field":"*","aggregation":"count","alias":"invoice_count"}],"orderBy":[{"field":"total_amount","direction":"desc"}],"limit":50}

## Exempt and zero-rated transactions (BT-118)
{"reportName":"VAT-Exempt and Zero-Rated Lines","entity":"tax_subtotals","filters":[{"field":"tax_subtotals.tax_category","operator":"in","value":["E","Z","K"]}],"groupBy":["tax_subtotals.tax_category","supplier.name"],"metrics":[{"field":"tax_subtotals.taxable_amount","aggregation":"sum","alias":"exempt_taxable"},{"field":"*","aggregation":"count","alias":"count"}],"orderBy":[{"field":"exempt_taxable","direction":"desc"}],"limit":200}

=== OUTPUT INSTRUCTIONS ===
Respond with ONLY the JSON object — no markdown fences, no explanation, no preamble.
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
        raise ValueError("OPENAI_API_KEY is not set")

    try:
        client = _get_client()
        today = date.today()
        system_with_date = (
            f"Today's date is {today.isoformat()}. "
            f"Current year: {today.year}. "
            f"When the user says 'Q1' without specifying a year, use Q1 of {today.year} "
            f"({today.year}-01-01 to {today.year}-03-31). "
            f"When the user says 'this quarter', derive the current quarter from today's date.\n\n"
            + REPORT_SYSTEM_PROMPT
        )
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_with_date},
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
