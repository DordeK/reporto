"""
Slovenian DDV (VAT) reporting service.

Generates two official eDavki XML documents:
  1. KPR — Knjiga Prejetih Računov (Purchase Ledger), submitted monthly/quarterly
     Schema: http://edavki.durs.si/Documents/Schemas/KPR_3.xsd
  2. DDV-O — Periodična DDV napoved (Periodic VAT Return)
     Schema: http://edavki.durs.si/Documents/Schemas/DDVO_4.xsd

Submission portal: https://beta.edavki.durs.si
Tax authority: FURS — Finančna uprava Republike Slovenije
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Any
import xml.etree.ElementTree as ET

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


# Slovenian DDV rates (ZDDV-1)
RATE_STANDARD = Decimal("22")    # standard rate
RATE_REDUCED1 = Decimal("9.5")   # first reduced rate (food, books, hotels…)
RATE_REDUCED2 = Decimal("5")     # second reduced rate (books, periodicals)


def _d(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _fmt(v: Decimal) -> str:
    return str(v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _peppol_rate_to_si(peppol_percent: Any) -> str:
    """
    Map Peppol/UBL tax percent to Slovenian DDV bucket.
    Belgian invoices use 21/12/6 — we map to the nearest Slovenian equivalent
    for cross-border demo purposes.
    """
    p = int(_d(peppol_percent))
    if p >= 20:
        return "22"
    if p >= 8:
        return "9.5"
    if p >= 4:
        return "5"
    return "0"


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------

async def fetch_purchase_ledger(
    db: AsyncSession,
    period_start: date,
    period_end: date,
) -> list[dict]:
    """
    Pull all received invoices with their tax subtotals for the period.
    Returns one dict per invoice with bucketed VAT amounts.
    """
    rows_r = await db.execute(text("""
        SELECT
            i.invoice_number,
            i.issue_date,
            i.payable_amount,
            i.tax_exclusive_amount,
            i.tax_amount,
            p.name            AS supplier_name,
            p.vat_id          AS supplier_vat,
            p.company_id      AS supplier_tax_number
        FROM invoices i
        JOIN parties p ON p.id = i.supplier_id
        WHERE i.direction = 'received'
          AND i.issue_date BETWEEN :start AND :end
        ORDER BY i.issue_date, i.invoice_number
    """), {"start": period_start, "end": period_end})
    invoices = [dict(r._mapping) for r in rows_r.fetchall()]

    # Fetch tax subtotals per invoice
    sub_r = await db.execute(text("""
        SELECT
            i.invoice_number,
            ts.tax_percent,
            ts.tax_category,
            ts.taxable_amount,
            ts.tax_amount
        FROM tax_subtotals ts
        JOIN invoices i ON i.id = ts.invoice_id
        WHERE i.direction = 'received'
          AND i.issue_date BETWEEN :start AND :end
    """), {"start": period_start, "end": period_end})
    subtotals_raw = sub_r.fetchall()

    # Index subtotals by invoice number
    subs: dict[str, list] = {}
    for s in subtotals_raw:
        subs.setdefault(s.invoice_number, []).append(s)

    result = []
    for inv in invoices:
        num = inv["invoice_number"]
        buckets: dict[str, dict] = {
            "22":  {"taxable": Decimal("0"), "vat": Decimal("0")},
            "9.5": {"taxable": Decimal("0"), "vat": Decimal("0")},
            "5":   {"taxable": Decimal("0"), "vat": Decimal("0")},
            "0":   {"taxable": Decimal("0"), "vat": Decimal("0")},
            "exempt": {"taxable": Decimal("0"), "vat": Decimal("0")},
        }

        for s in subs.get(num, []):
            cat = (s.tax_category or "S").upper()
            if cat in ("E", "K", "Z"):
                bucket = "exempt"
            else:
                bucket = _peppol_rate_to_si(s.tax_percent)

            buckets[bucket]["taxable"] += _d(s.taxable_amount)
            buckets[bucket]["vat"]     += _d(s.tax_amount)

        result.append({
            "invoice_number":    num,
            "invoice_date":      inv["issue_date"].isoformat() if inv["issue_date"] else "",
            "supplier_name":     inv["supplier_name"] or "",
            "supplier_vat":      inv["supplier_vat"] or "",
            "supplier_tax":      inv["supplier_tax_number"] or "",
            "payable_amount":    _d(inv["payable_amount"]),
            "buckets":           buckets,
        })

    return result


async def compute_ddvo_boxes(
    db: AsyncSession,
    period_start: date,
    period_end: date,
) -> dict:
    """
    Compute DDV-O box values from received invoices.
    Box references follow the official FURS DDV-O form (ZDDV-1).
    """
    r = await db.execute(text("""
        SELECT
            ts.tax_percent,
            ts.tax_category,
            COALESCE(SUM(ts.taxable_amount), 0) AS taxable,
            COALESCE(SUM(ts.tax_amount),     0) AS vat
        FROM tax_subtotals ts
        JOIN invoices i ON i.id = ts.invoice_id
        WHERE i.direction = 'received'
          AND i.issue_date BETWEEN :start AND :end
        GROUP BY ts.tax_percent, ts.tax_category
    """), {"start": period_start, "end": period_end})
    rows = r.fetchall()

    boxes: dict[str, Decimal] = {k: Decimal("0") for k in [
        "41", "42",   # taxable base + VAT at 22%
        "43", "44",   # taxable base + VAT at 9.5%
        "45", "46",   # taxable base + VAT at 5%
        "50",         # exempt purchases
        "52",         # input VAT deductible (total)
        "60",         # total purchases incl. VAT
    ]}

    for row in rows:
        cat = (row.tax_category or "S").upper()
        bucket = _peppol_rate_to_si(row.tax_percent)
        taxable = _d(row.taxable)
        vat     = _d(row.vat)

        if cat in ("E", "K", "Z"):
            boxes["50"] += taxable
        elif bucket == "22":
            boxes["41"] += taxable
            boxes["42"] += vat
        elif bucket == "9.5":
            boxes["43"] += taxable
            boxes["44"] += vat
        elif bucket == "5":
            boxes["45"] += taxable
            boxes["46"] += vat

        boxes["52"] += vat
        boxes["60"] += taxable + vat

    return {k: _fmt(v) for k, v in boxes.items()}


# ---------------------------------------------------------------------------
# KPR XML generator
# ---------------------------------------------------------------------------

def generate_kpr_xml(
    entries: list[dict],
    tax_number: str,
    period_start: date,
    period_end: date,
) -> str:
    """
    Generate eDavki KPR XML (Knjiga Prejetih Računov).
    Envelope follows Docs_2.xsd; body follows KPR_3.xsd.
    """
    # Namespaces
    NS_DOCS = "http://edavki.durs.si/Documents/Schemas/Docs_2.xsd"
    NS_KPR  = "http://edavki.durs.si/Documents/Schemas/KPR_3.xsd"

    ET.register_namespace("",    NS_DOCS)
    ET.register_namespace("kpr", NS_KPR)

    def el(tag: str, text_val: str | None = None, ns: str = NS_DOCS) -> ET.Element:
        e = ET.Element(f"{{{ns}}}{tag}")
        if text_val is not None:
            e.text = text_val
        return e

    def sub(parent: ET.Element, tag: str, text_val: str | None = None, ns: str = NS_DOCS) -> ET.Element:
        e = ET.SubElement(parent, f"{{{ns}}}{tag}")
        if text_val is not None:
            e.text = text_val
        return e

    # Root envelope
    envelope = el("Envelope")
    envelope.set("xmlns",     NS_DOCS)
    envelope.set("xmlns:kpr", NS_KPR)
    envelope.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

    # Header
    header = sub(envelope, "Header")
    taxpayer = sub(header, "taxpayer")
    sub(taxpayer, "taxNumber", tax_number)
    workflow = sub(header, "Workflow")
    sub(workflow, "DocumentWorkflowID", "O")   # O = original submission

    # Body
    body = sub(envelope, "body")
    body_content = sub(body, "bodyContent")

    kpr = sub(body_content, "KPR", ns=NS_KPR)
    kpr.set("xmlns", NS_KPR)

    # KPR Header
    kpr_header = sub(kpr, "Header", ns=NS_KPR)
    sub(kpr_header, "TaxNumber",    tax_number,              ns=NS_KPR)
    sub(kpr_header, "PeriodStart",  period_start.isoformat(), ns=NS_KPR)
    sub(kpr_header, "PeriodEnd",    period_end.isoformat(),   ns=NS_KPR)
    # Tax period in YYYYMM format (use period_start month)
    sub(kpr_header, "TaxPeriod",
        f"{period_start.year}{period_start.month:02d}", ns=NS_KPR)
    sub(kpr_header, "DocumentDate", date.today().isoformat(), ns=NS_KPR)

    # Purchase entries
    for seq, entry in enumerate(entries, start=1):
        purchase = sub(kpr, "Purchase", ns=NS_KPR)
        sub(purchase, "SeqNumber",          str(seq),                    ns=NS_KPR)
        sub(purchase, "InvoiceNumber",      entry["invoice_number"],     ns=NS_KPR)
        sub(purchase, "InvoiceDate",        entry["invoice_date"],       ns=NS_KPR)
        sub(purchase, "SupplierName",       entry["supplier_name"],      ns=NS_KPR)
        sub(purchase, "SupplierTaxNumber",  _normalise_si_tax(
            entry["supplier_vat"] or entry["supplier_tax"]),             ns=NS_KPR)

        b = entry["buckets"]
        # Standard 22%
        sub(purchase, "TaxableAmount22",    _fmt(b["22"]["taxable"]),  ns=NS_KPR)
        sub(purchase, "TaxAmount22",        _fmt(b["22"]["vat"]),      ns=NS_KPR)
        # Reduced 9.5%
        sub(purchase, "TaxableAmount95",    _fmt(b["9.5"]["taxable"]), ns=NS_KPR)
        sub(purchase, "TaxAmount95",        _fmt(b["9.5"]["vat"]),     ns=NS_KPR)
        # Reduced 5%
        sub(purchase, "TaxableAmount5",     _fmt(b["5"]["taxable"]),   ns=NS_KPR)
        sub(purchase, "TaxAmount5",         _fmt(b["5"]["vat"]),       ns=NS_KPR)
        # Exempt / zero-rated
        sub(purchase, "ExemptAmount",       _fmt(
            b["0"]["taxable"] + b["exempt"]["taxable"]),                ns=NS_KPR)
        sub(purchase, "TotalInvoiceAmount", _fmt(entry["payable_amount"]), ns=NS_KPR)

    # Totals footer
    totals = sub(kpr, "Totals", ns=NS_KPR)
    sub(totals, "TotalEntries",      str(len(entries)),                                   ns=NS_KPR)
    sub(totals, "TotalTaxableBase",  _fmt(sum(_d(e["buckets"]["22"]["taxable"])
                                              + _d(e["buckets"]["9.5"]["taxable"])
                                              + _d(e["buckets"]["5"]["taxable"])
                                              for e in entries)),                          ns=NS_KPR)
    sub(totals, "TotalVATAmount",    _fmt(sum(_d(e["buckets"]["22"]["vat"])
                                              + _d(e["buckets"]["9.5"]["vat"])
                                              + _d(e["buckets"]["5"]["vat"])
                                              for e in entries)),                          ns=NS_KPR)
    sub(totals, "TotalInvoiceAmount", _fmt(sum(e["payable_amount"] for e in entries)),   ns=NS_KPR)

    tree = ET.ElementTree(envelope)
    ET.indent(tree, space="  ")
    import io
    buf = io.BytesIO()
    tree.write(buf, xml_declaration=True, encoding="UTF-8")
    return buf.getvalue().decode("utf-8")


# ---------------------------------------------------------------------------
# DDV-O XML generator (Periodic VAT Return)
# ---------------------------------------------------------------------------

def generate_ddvo_xml(
    boxes: dict,
    tax_number: str,
    taxpayer_name: str,
    period_start: date,
    period_end: date,
) -> str:
    """
    Generate eDavki DDV-O XML (Periodična DDV napoved).
    Schema: DDVO_4.xsd
    Box numbering follows official FURS DDV-O form (ZDDV-1, Art. 88).
    """
    NS_DOCS = "http://edavki.durs.si/Documents/Schemas/Docs_2.xsd"
    NS_DDVO = "http://edavki.durs.si/Documents/Schemas/DDVO_4.xsd"

    ET.register_namespace("",     NS_DOCS)
    ET.register_namespace("ddvo", NS_DDVO)

    def sub(parent: ET.Element, tag: str, text_val: str | None = None, ns: str = NS_DOCS) -> ET.Element:
        e = ET.SubElement(parent, f"{{{ns}}}{tag}")
        if text_val is not None:
            e.text = text_val
        return e

    envelope = ET.Element(f"{{{NS_DOCS}}}Envelope")
    envelope.set("xmlns",      NS_DOCS)
    envelope.set("xmlns:ddvo", NS_DDVO)
    envelope.set("xmlns:xsi",  "http://www.w3.org/2001/XMLSchema-instance")

    header = sub(envelope, "Header")
    taxpayer = sub(header, "taxpayer")
    sub(taxpayer, "taxNumber", tax_number)
    sub(taxpayer, "taxpayerName", taxpayer_name)
    workflow = sub(header, "Workflow")
    sub(workflow, "DocumentWorkflowID", "O")
    sub(workflow, "DocumentWorkflowName", "Periodična DDV napoved")

    body = sub(envelope, "body")
    body_content = sub(body, "bodyContent")

    ddvo = sub(body_content, "DDVO", ns=NS_DDVO)
    ddvo.set("xmlns", NS_DDVO)

    # Period
    period = sub(ddvo, "Period", ns=NS_DDVO)
    sub(period, "PeriodStart",  period_start.isoformat(), ns=NS_DDVO)
    sub(period, "PeriodEnd",    period_end.isoformat(),   ns=NS_DDVO)
    sub(period, "Year",         str(period_start.year),   ns=NS_DDVO)
    sub(period, "Month",        str(period_start.month),  ns=NS_DDVO)

    # Taxpayer
    tp = sub(ddvo, "Taxpayer", ns=NS_DDVO)
    sub(tp, "TaxNumber",    tax_number,    ns=NS_DDVO)
    sub(tp, "TaxpayerName", taxpayer_name, ns=NS_DDVO)

    # ── Section III: Input VAT (Purchases) — boxes 40-52 ────────────────────
    sec3 = sub(ddvo, "SectionIII_InputVAT", ns=NS_DDVO)
    # Box 41/42: taxable base + VAT at standard rate (22%)
    sub(sec3, "Box41_TaxableBase_22pct",    boxes.get("41", "0.00"), ns=NS_DDVO)
    sub(sec3, "Box42_InputVAT_22pct",       boxes.get("42", "0.00"), ns=NS_DDVO)
    # Box 43/44: taxable base + VAT at reduced rate (9.5%)
    sub(sec3, "Box43_TaxableBase_95pct",    boxes.get("43", "0.00"), ns=NS_DDVO)
    sub(sec3, "Box44_InputVAT_95pct",       boxes.get("44", "0.00"), ns=NS_DDVO)
    # Box 45/46: taxable base + VAT at second reduced rate (5%)
    sub(sec3, "Box45_TaxableBase_5pct",     boxes.get("45", "0.00"), ns=NS_DDVO)
    sub(sec3, "Box46_InputVAT_5pct",        boxes.get("46", "0.00"), ns=NS_DDVO)
    # Box 50: exempt purchases
    sub(sec3, "Box50_ExemptPurchases",      boxes.get("50", "0.00"), ns=NS_DDVO)
    # Box 52: total deductible input VAT
    sub(sec3, "Box52_TotalDeductibleVAT",   boxes.get("52", "0.00"), ns=NS_DDVO)

    # ── Section V: Summary ───────────────────────────────────────────────────
    sec5 = sub(ddvo, "SectionV_Summary", ns=NS_DDVO)
    input_vat  = Decimal(boxes.get("52", "0"))
    output_vat = Decimal("0")   # demo: no sent invoices in dataset
    net_payable = output_vat - input_vat

    sub(sec5, "Box60_TotalPurchasesInclVAT", boxes.get("60", "0.00"), ns=NS_DDVO)
    sub(sec5, "TotalOutputVAT",  _fmt(output_vat),                    ns=NS_DDVO)
    sub(sec5, "TotalInputVAT",   boxes.get("52", "0.00"),             ns=NS_DDVO)
    if net_payable >= 0:
        sub(sec5, "VATPayable",   _fmt(net_payable),  ns=NS_DDVO)
        sub(sec5, "VATRefundable", "0.00",            ns=NS_DDVO)
    else:
        sub(sec5, "VATPayable",    "0.00",            ns=NS_DDVO)
        sub(sec5, "VATRefundable", _fmt(-net_payable), ns=NS_DDVO)

    tree = ET.ElementTree(envelope)
    ET.indent(tree, space="  ")
    import io
    buf = io.BytesIO()
    tree.write(buf, xml_declaration=True, encoding="UTF-8")
    return buf.getvalue().decode("utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_si_tax(raw: str) -> str:
    """Normalise a tax/VAT number to Slovenian format (SI + 8 digits)."""
    if not raw:
        return "SI00000000"
    clean = raw.upper().replace(" ", "").replace("-", "")
    if clean.startswith("SI"):
        return clean
    if clean.startswith("BE") or clean.startswith("DE") or clean.startswith("NL"):
        # Foreign supplier — keep as-is for cross-border entries
        return clean
    digits = "".join(c for c in clean if c.isdigit())
    return f"SI{digits[:8].zfill(8)}"
