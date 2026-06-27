#!/usr/bin/env python3
"""
Generate 1000 random UBL 2.1 invoices and upload them to the local backend.
Usage:  python generate_invoices.py
        python generate_invoices.py --count 500 --url http://localhost:8000
"""
import argparse
import random
import sys
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import httpx

# ── Configurable ─────────────────────────────────────────────────────────────
DEFAULT_URL   = "http://localhost:8000"
DEFAULT_COUNT = 1000
BATCH_SIZE    = 20   # files per multipart POST

# ── Reference data ───────────────────────────────────────────────────────────
SUPPLIERS = [
    ("TechSoft Solutions NV",   "BE0123456789", "BE"),
    ("CloudServices BVBA",      "BE0234567890", "BE"),
    ("ConsultGroup SA",         "BE0345678901", "BE"),
    ("OfficeSupply NV",         "BE0456789012", "BE"),
    ("TravelCorp BVBA",         "BE0567890123", "BE"),
    ("QuickPrint",              "BE0678901234", "BE"),
    ("DataStream NV",           "BE0789012345", "BE"),
    ("LegalEdge BVBA",          "BE0890123456", "BE"),
    ("GreenEnergy SA",          "BE0901234567", "BE"),
    ("LogiMove NV",             "NL123456789B01", "NL"),
    ("Softwerk GmbH",           "DE123456789",  "DE"),
    ("Nordic IT AB",            "SE556677889901","SE"),
    ("FinServ Luxembourg SA",   "LU12345678",   "LU"),
    ("MediaGroup France SARL",  "FR12345678901","FR"),
    ("IberTech SL",             "ESB12345678",  "ES"),
]

CUSTOMER = ("Demo Company NV", "BE0987654321", "BE")

ITEMS = [
    ("Software license renewal",       "S", 21, (500,  5000)),
    ("Cloud infrastructure services",  "S", 21, (200,  3000)),
    ("Consulting services",            "S", 21, (800, 10000)),
    ("Office supplies",                "S", 21, (50,    500)),
    ("Travel expenses reimbursement",  "Z",  0, (200,  2000)),
    ("Marketing campaign management",  "S", 21, (1000, 8000)),
    ("Legal advisory services",        "S", 21, (500,  4000)),
    ("Print & design services",        "S", 21, (100,  1500)),
    ("Data analytics platform",        "S", 21, (1000, 6000)),
    ("Logistics & freight",            "S", 21, (300,  2000)),
    ("Hardware maintenance",           "S", 21, (200,  3000)),
    ("Training & workshops",           "S", 21, (400,  4000)),
    ("Catering services",              "AE", 21, (300,  2000)),  # reverse charge demo
    ("Electricity supply",             "S",  6, (100,   800)),
    ("Books & periodicals",            "S",  6, (20,    200)),
    ("Hotel accommodation",            "S", 12, (150,  2000)),
]

PAYMENT_CODES = ["30", "30", "30", "49", "58"]  # weighted towards credit transfer

def rnd(lo: float, hi: float, decimals: int = 2) -> Decimal:
    v = random.uniform(lo, hi)
    return Decimal(str(v)).quantize(Decimal("0." + "0" * decimals), rounding=ROUND_HALF_UP)

def fmt(d: Decimal) -> str:
    return str(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))

def make_invoice(seq: int, issue_date: date) -> str:
    supplier_name, supplier_vat, supplier_country = random.choice(SUPPLIERS)
    customer_name, customer_vat, customer_country = CUSTOMER

    payment_terms = random.randint(14, 60)
    due_date = issue_date + timedelta(days=payment_terms)

    # 1-3 line items
    num_lines = random.randint(1, 3)
    lines = random.sample(ITEMS, num_lines)

    line_totals = []
    for item_desc, tax_cat, tax_pct, (lo, hi) in lines:
        net = rnd(lo, hi)
        line_totals.append((item_desc, tax_cat, tax_pct, net))

    # Aggregate tax subtotals
    tax_buckets: dict[tuple, Decimal] = {}
    for _, tax_cat, tax_pct, net in line_totals:
        key = (tax_cat, tax_pct)
        tax_buckets[key] = tax_buckets.get(key, Decimal("0")) + net

    total_net  = sum(net for _, _, _, net in line_totals)
    total_vat  = sum(
        (net * Decimal(str(pct)) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if cat != "AE" else Decimal("0")
        for (cat, pct), net in tax_buckets.items()
    )
    total_gross = total_net + total_vat

    # Occasionally inject anomalies for demo variety
    anomaly_roll = random.random()
    if anomaly_roll < 0.04:                          # 4% duplicate ID
        inv_id = f"INV-GEN-{random.randint(1, seq - 1):04d}" if seq > 1 else f"INV-GEN-{seq:04d}"
    else:
        inv_id = f"INV-GEN-{seq:04d}"

    if anomaly_roll > 0.96:                          # 4% bad due date
        due_date = issue_date - timedelta(days=random.randint(1, 10))

    payment_code = random.choice(PAYMENT_CODES)

    # ── Build XML ─────────────────────────────────────────────────────────────
    tax_subtotals_xml = ""
    for (cat, pct), net in tax_buckets.items():
        vat_amt = (net * Decimal(str(pct)) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) \
                  if cat != "AE" else Decimal("0")
        tax_subtotals_xml += f"""    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">{fmt(net)}</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">{fmt(vat_amt)}</cbc:TaxAmount>
      <cac:TaxCategory>
        <cbc:ID>{cat}</cbc:ID>
        <cbc:Percent>{pct}</cbc:Percent>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
      </cac:TaxCategory>
    </cac:TaxSubtotal>\n"""

    lines_xml = ""
    for line_no, (desc, cat, pct, net) in enumerate(line_totals, start=1):
        qty = random.randint(1, 10)
        unit_price = (net / qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        lines_xml += f"""  <cac:InvoiceLine>
    <cbc:ID>{line_no}</cbc:ID>
    <cbc:InvoicedQuantity unitCode="EA">{qty}</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">{fmt(net)}</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Description>{desc}</cbc:Description>
      <cbc:Name>{desc}</cbc:Name>
      <cac:ClassifiedTaxCategory>
        <cbc:ID>{cat}</cbc:ID>
        <cbc:Percent>{pct}</cbc:Percent>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
      </cac:ClassifiedTaxCategory>
    </cac:Item>
    <cac:Price>
      <cbc:PriceAmount currencyID="EUR">{fmt(unit_price)}</cbc:PriceAmount>
    </cac:Price>
  </cac:InvoiceLine>\n"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
  <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0</cbc:CustomizationID>
  <cbc:ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</cbc:ProfileID>
  <cbc:ID>{inv_id}</cbc:ID>
  <cbc:IssueDate>{issue_date}</cbc:IssueDate>
  <cbc:DueDate>{due_date}</cbc:DueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cac:PartyName><cbc:Name>{supplier_name}</cbc:Name></cac:PartyName>
      <cac:PostalAddress>
        <cac:Country><cbc:IdentificationCode>{supplier_country}</cbc:IdentificationCode></cac:Country>
      </cac:PostalAddress>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>{supplier_vat}</cbc:CompanyID>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>{supplier_name}</cbc:RegistrationName>
        <cbc:CompanyID>{supplier_vat}</cbc:CompanyID>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cac:PartyName><cbc:Name>{customer_name}</cbc:Name></cac:PartyName>
      <cac:PostalAddress>
        <cac:Country><cbc:IdentificationCode>{customer_country}</cbc:IdentificationCode></cac:Country>
      </cac:PostalAddress>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>{customer_vat}</cbc:CompanyID>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>{customer_name}</cbc:RegistrationName>
        <cbc:CompanyID>{customer_vat}</cbc:CompanyID>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:PaymentMeans>
    <cbc:PaymentMeansCode>{payment_code}</cbc:PaymentMeansCode>
  </cac:PaymentMeans>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">{fmt(total_vat)}</cbc:TaxAmount>
{tax_subtotals_xml}  </cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="EUR">{fmt(total_net)}</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">{fmt(total_net)}</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">{fmt(total_gross)}</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="EUR">{fmt(total_gross)}</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
{lines_xml}</Invoice>"""


def upload_batch(url: str, batch: list[tuple[str, bytes]]) -> dict:
    files = [("files", (name, xml, "application/xml")) for name, xml in batch]
    with httpx.Client(timeout=60) as client:
        r = client.post(f"{url}/invoices/upload", files=files)
        r.raise_for_status()
        return r.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--url",   type=str, default=DEFAULT_URL)
    args = parser.parse_args()

    print(f"Generating {args.count} invoices → {args.url}/invoices/upload")

    # Spread issue dates over the last 18 months
    end_date   = date.today()
    start_date = end_date - timedelta(days=548)

    invoices: list[tuple[str, bytes]] = []
    for i in range(1, args.count + 1):
        issue_date = random_date(start_date, end_date)
        xml = make_invoice(i, issue_date)
        invoices.append((f"INV-GEN-{i:04d}.xml", xml.encode("utf-8")))

    total_ok = 0
    total_err = 0
    batches = [invoices[i:i + BATCH_SIZE] for i in range(0, len(invoices), BATCH_SIZE)]

    for idx, batch in enumerate(batches, start=1):
        try:
            result = upload_batch(args.url, batch)
            ok  = sum(1 for d in result.get("details", []) if d.get("status") == "ok")
            err = sum(1 for d in result.get("details", []) if d.get("status") == "error")
            total_ok  += ok
            total_err += err
            pct = idx * BATCH_SIZE * 100 // args.count
            print(f"  batch {idx}/{len(batches)}  ({pct}%)  +{ok} ok  +{err} err", end="\r", flush=True)
        except Exception as e:
            print(f"\n  batch {idx} failed: {e}")
            total_err += len(batch)

    print(f"\nDone. {total_ok} imported, {total_err} errors.")


if __name__ == "__main__":
    main()
