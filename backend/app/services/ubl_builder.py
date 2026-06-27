"""
Build a Peppol BIS Billing 3.0 / UBL 2.1 Invoice XML document from structured data.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from lxml import etree

NS_UBL = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
NS_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

CUSTOMIZATION_ID = "urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0"
PROFILE_ID = "urn:fdc:peppol.eu:2017:poacc:billing:01:1.0"


_COUNTRY_NAME_ISO: dict[str, str] = {
    "SLOVENIA": "SI", "SLOVENIJA": "SI",
    "BELGIUM": "BE", "BELGIE": "BE", "BELGIQUE": "BE",
    "NETHERLANDS": "NL", "NEDERLAND": "NL", "HOLLAND": "NL",
    "GERMANY": "DE", "DEUTSCHLAND": "DE",
    "FRANCE": "FR", "AUSTRIA": "AT", "ITALY": "IT", "ITALIA": "IT",
    "SPAIN": "ES", "ESPANA": "ES", "PORTUGAL": "PT",
    "CROATIA": "HR", "HRVATSKA": "HR", "SERBIA": "RS",
    "CZECHIA": "CZ", "CZECH REPUBLIC": "CZ",
    "POLAND": "PL", "POLSKA": "PL",
    "HUNGARY": "HU", "MAGYARORSZÁG": "HU",
    "ROMANIA": "RO", "BULGARIA": "BG",
    "DENMARK": "DK", "SVERIGE": "SE", "SWEDEN": "SE",
    "FINLAND": "FI", "SUOMI": "FI",
    "NORWAY": "NO", "NORGE": "NO",
    "SWITZERLAND": "CH", "SCHWEIZ": "CH",
    "UNITED KINGDOM": "GB", "UK": "GB", "GREAT BRITAIN": "GB",
    "UNITED STATES": "US", "USA": "US",
}


def _iso_country(raw: str | None, default: str = "BE") -> str:
    if not raw:
        return default
    s = raw.strip().upper()
    if len(s) == 2:
        return s
    return _COUNTRY_NAME_ISO.get(s, s[:2])


def _r2(v) -> str:
    return str(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _r4(v) -> str:
    return str(Decimal(str(v)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def _cbc(tag: str, text: str, **attrs) -> etree._Element:
    el = etree.Element(f"{{{NS_CBC}}}{tag}", **attrs)
    el.text = text
    return el


def _cac(tag: str) -> etree._Element:
    return etree.Element(f"{{{NS_CAC}}}{tag}")


def _party_element(party: dict[str, Any]) -> etree._Element:
    p = _cac("Party")

    endpoint_raw = party.get("endpoint_id") or party.get("vat_id")
    if endpoint_raw:
        if ":" in endpoint_raw:
            scheme, eid = endpoint_raw.split(":", 1)
        else:
            scheme = party.get("endpoint_scheme") or "0208"
            eid = endpoint_raw
        ep = _cbc("EndpointID", eid)
        ep.set("schemeID", scheme)
        p.append(ep)

    if party.get("name"):
        pn = _cac("PartyName")
        pn.append(_cbc("Name", party["name"]))
        p.append(pn)

    addr = _cac("PostalAddress")
    if party.get("street_name"):
        addr.append(_cbc("StreetName", party["street_name"]))
    if party.get("city_name"):
        addr.append(_cbc("CityName", party["city_name"]))
    if party.get("postal_zone"):
        addr.append(_cbc("PostalZone", party["postal_zone"]))
    country = _cac("Country")
    country.append(_cbc("IdentificationCode", _iso_country(party.get("country_code"))))
    addr.append(country)
    p.append(addr)

    if party.get("vat_id"):
        pts = _cac("PartyTaxScheme")
        pts.append(_cbc("CompanyID", party["vat_id"]))
        ts = _cac("TaxScheme")
        ts.append(_cbc("ID", "VAT"))
        pts.append(ts)
        p.append(pts)

    ple = _cac("PartyLegalEntity")
    ple.append(_cbc("RegistrationName", party.get("name") or ""))
    if party.get("company_id") or party.get("vat_id"):
        ple.append(_cbc("CompanyID", party.get("company_id") or party.get("vat_id") or ""))
    p.append(ple)

    if party.get("contact_name") or party.get("contact_email") or party.get("contact_telephone"):
        contact = _cac("Contact")
        if party.get("contact_name"):
            contact.append(_cbc("Name", party["contact_name"]))
        if party.get("contact_telephone"):
            contact.append(_cbc("Telephone", party["contact_telephone"]))
        if party.get("contact_email"):
            contact.append(_cbc("ElectronicMail", party["contact_email"]))
        p.append(contact)

    return p


def build_ubl_invoice(data: dict[str, Any]) -> str:
    """
    Build a Peppol BIS Billing 3.0 UBL 2.1 Invoice XML string.

    Expected data keys:
      invoice_number, issue_date, due_date, currency (default EUR)
      supplier: {name, vat_id, street_name, city_name, postal_zone, country_code,
                  endpoint_id, endpoint_scheme, company_id, iban,
                  contact_name, contact_telephone, contact_email}
      customer: {name, vat_id, street_name, city_name, postal_zone, country_code,
                  endpoint_id, endpoint_scheme, company_id}
      lines: [{description, quantity, unit_price, tax_percent, tax_category, unit_code}]
      note (optional)
      payment_terms_note (optional)
      buyer_reference (optional)
    """
    currency = data.get("currency", "EUR")
    lines_raw = data.get("lines", [])

    # ── Compute totals ────────────────────────────────────────────────────────
    line_extension = Decimal("0")
    tax_groups: dict[str, dict] = {}  # key = (category, percent)

    computed_lines = []
    for i, ln in enumerate(lines_raw):
        qty = Decimal(str(ln.get("quantity", 1)))
        price = Decimal(str(ln.get("unit_price", 0)))
        amount = (qty * price).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        tax_pct = Decimal(str(ln.get("tax_percent", 21)))
        tax_cat = ln.get("tax_category", "S")

        line_extension += amount

        key = f"{tax_cat}:{tax_pct}"
        if key not in tax_groups:
            tax_groups[key] = {"category": tax_cat, "percent": tax_pct, "taxable": Decimal("0"), "tax": Decimal("0")}
        tax_groups[key]["taxable"] += amount

        computed_lines.append({**ln, "line_number": str(i + 1), "qty": qty, "price": price, "amount": amount, "tax_pct": tax_pct, "tax_cat": tax_cat})

    for g in tax_groups.values():
        g["tax"] = (g["taxable"] * g["percent"] / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    total_tax = sum(g["tax"] for g in tax_groups.values())
    tax_exclusive = line_extension
    tax_inclusive = line_extension + total_tax
    payable = tax_inclusive

    # ── Root element ──────────────────────────────────────────────────────────
    nsmap = {
        None: NS_UBL,
        "cac": NS_CAC,
        "cbc": NS_CBC,
    }
    root = etree.Element(f"{{{NS_UBL}}}Invoice", nsmap=nsmap)

    root.append(_cbc("CustomizationID", CUSTOMIZATION_ID))
    root.append(_cbc("ProfileID", PROFILE_ID))
    root.append(_cbc("ID", data.get("invoice_number", "INV-001")))
    root.append(_cbc("IssueDate", data.get("issue_date", "")))
    if data.get("due_date"):
        root.append(_cbc("DueDate", data["due_date"]))
    root.append(_cbc("InvoiceTypeCode", "380"))  # commercial invoice
    if data.get("note"):
        root.append(_cbc("Note", data["note"]))
    root.append(_cbc("DocumentCurrencyCode", currency))
    # PEPPOL-EN16931-R003: BuyerReference or OrderReference is required
    buyer_ref = data.get("buyer_reference") or data.get("invoice_number", "N/A")
    root.append(_cbc("BuyerReference", buyer_ref))

    # ── Supplier ──────────────────────────────────────────────────────────────
    supplier_party = _cac("AccountingSupplierParty")
    supplier_party.append(_party_element(data.get("supplier", {})))
    root.append(supplier_party)

    # ── Customer ──────────────────────────────────────────────────────────────
    customer_party = _cac("AccountingCustomerParty")
    customer_party.append(_party_element(data.get("customer", {})))
    root.append(customer_party)

    # ── Payment means ─────────────────────────────────────────────────────────
    supplier = data.get("supplier", {})
    if supplier.get("iban"):
        # BR-61: code 30 (SEPA credit transfer) requires PayeeFinancialAccount/ID
        pm = _cac("PaymentMeans")
        pm.append(_cbc("PaymentMeansCode", "30"))
        pfa = _cac("PayeeFinancialAccount")
        pfa.append(_cbc("ID", supplier["iban"]))
        pm.append(pfa)
        root.append(pm)

    # BR-CO-25: PayableAmount > 0 requires DueDate OR PaymentTerms/Note
    terms_note = data.get("payment_terms_note")
    if not data.get("due_date") and not terms_note:
        terms_note = "Net 30"
    if terms_note:
        pt = _cac("PaymentTerms")
        pt.append(_cbc("Note", terms_note))
        root.append(pt)

    # ── Tax total ─────────────────────────────────────────────────────────────
    tax_total = _cac("TaxTotal")
    ta_el = _cbc("TaxAmount", _r2(total_tax))
    ta_el.set("currencyID", currency)
    tax_total.append(ta_el)

    for g in tax_groups.values():
        subtotal = _cac("TaxSubtotal")
        taxable_el = _cbc("TaxableAmount", _r2(g["taxable"]))
        taxable_el.set("currencyID", currency)
        subtotal.append(taxable_el)
        tax_amount_el = _cbc("TaxAmount", _r2(g["tax"]))
        tax_amount_el.set("currencyID", currency)
        subtotal.append(tax_amount_el)
        tax_cat_el = _cac("TaxCategory")
        tax_cat_el.append(_cbc("ID", g["category"]))
        tax_cat_el.append(_cbc("Percent", str(g["percent"])))
        ts = _cac("TaxScheme")
        ts.append(_cbc("ID", "VAT"))
        tax_cat_el.append(ts)
        subtotal.append(tax_cat_el)
        tax_total.append(subtotal)

    root.append(tax_total)

    # ── Legal monetary total ──────────────────────────────────────────────────
    lmt = _cac("LegalMonetaryTotal")
    for tag, val in [
        ("LineExtensionAmount", line_extension),
        ("TaxExclusiveAmount", tax_exclusive),
        ("TaxInclusiveAmount", tax_inclusive),
        ("PayableAmount", payable),
    ]:
        el = _cbc(tag, _r2(val))
        el.set("currencyID", currency)
        lmt.append(el)
    root.append(lmt)

    # ── Invoice lines ─────────────────────────────────────────────────────────
    for ln in computed_lines:
        line_el = _cac("InvoiceLine")
        line_el.append(_cbc("ID", ln["line_number"]))
        qty_el = _cbc("InvoicedQuantity", _r4(ln["qty"]))
        qty_el.set("unitCode", ln.get("unit_code") or "C62")
        line_el.append(qty_el)
        lea = _cbc("LineExtensionAmount", _r2(ln["amount"]))
        lea.set("currencyID", currency)
        line_el.append(lea)

        item = _cac("Item")
        item.append(_cbc("Name", ln.get("description") or ln.get("item_name") or ""))
        ctc = _cac("ClassifiedTaxCategory")
        ctc.append(_cbc("ID", ln["tax_cat"]))
        ctc.append(_cbc("Percent", str(ln["tax_pct"])))
        ts2 = _cac("TaxScheme")
        ts2.append(_cbc("ID", "VAT"))
        ctc.append(ts2)
        item.append(ctc)
        line_el.append(item)

        price_el = _cac("Price")
        pa = _cbc("PriceAmount", _r4(ln["price"]))
        pa.set("currencyID", currency)
        price_el.append(pa)
        line_el.append(price_el)

        root.append(line_el)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True).decode("utf-8")
