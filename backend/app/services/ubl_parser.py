"""
UBL 2.1 XML invoice parser.
Handles the standard UBL 2.1 namespaces for Invoice documents.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from lxml import etree


NS = {
    "ubl": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}


def _text(element, xpath: str) -> str | None:
    """Extract text from a single XPath result."""
    result = element.xpath(xpath, namespaces=NS)
    if result:
        val = result[0]
        if hasattr(val, "text"):
            return val.text.strip() if val.text else None
        return str(val).strip() if str(val) else None
    return None


def _decimal(element, xpath: str) -> Decimal | None:
    """Extract a Decimal value from an XPath result."""
    raw = _text(element, xpath)
    if raw is None:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _parse_party(party_element) -> dict[str, Any]:
    """Parse a cac:Party element into a dict."""
    if party_element is None:
        return {
            "name": None,
            "vat_id": None,
            "country_code": None,
            "endpoint_id": None,
            "iban": None,
            "street_name": None,
            "additional_street_name": None,
            "city_name": None,
            "postal_zone": None,
            "country_subentity": None,
            "registration_name": None,
            "company_id": None,
            "company_legal_form": None,
            "contact_name": None,
            "contact_telephone": None,
            "contact_email": None,
            "endpoint_scheme": None,
        }
    endpoint_el_list = party_element.xpath("cbc:EndpointID", namespaces=NS)
    endpoint_el = endpoint_el_list[0] if endpoint_el_list else None
    return {
        "name": _text(party_element, "cac:PartyName/cbc:Name/text()"),
        "vat_id": _text(party_element, "cac:PartyTaxScheme/cbc:CompanyID/text()"),
        "country_code": _text(party_element, "cac:PostalAddress/cac:Country/cbc:IdentificationCode/text()"),
        "endpoint_id": _text(party_element, "cbc:EndpointID/text()"),
        "iban": None,  # IBAN lives on PaymentMeans at invoice level
        "street_name": _text(party_element, "cac:PostalAddress/cbc:StreetName/text()"),
        "additional_street_name": _text(party_element, "cac:PostalAddress/cbc:AdditionalStreetName/text()"),
        "city_name": _text(party_element, "cac:PostalAddress/cbc:CityName/text()"),
        "postal_zone": _text(party_element, "cac:PostalAddress/cbc:PostalZone/text()"),
        "country_subentity": _text(party_element, "cac:PostalAddress/cbc:CountrySubentity/text()"),
        "registration_name": _text(party_element, "cac:PartyLegalEntity/cbc:RegistrationName/text()"),
        "company_id": _text(party_element, "cac:PartyLegalEntity/cbc:CompanyID/text()"),
        "company_legal_form": _text(party_element, "cac:PartyLegalEntity/cbc:CompanyLegalForm/text()"),
        "contact_name": _text(party_element, "cac:Contact/cbc:Name/text()"),
        "contact_telephone": _text(party_element, "cac:Contact/cbc:Telephone/text()"),
        "contact_email": _text(party_element, "cac:Contact/cbc:ElectronicMail/text()"),
        "endpoint_scheme": endpoint_el.get("schemeID", None) if endpoint_el is not None else None,
    }


def parse_ubl(xml_content: str) -> dict[str, Any]:
    """
    Parse a UBL 2.1 Invoice XML string and return a structured dict.

    Raises:
        ValueError: if the XML cannot be parsed or the root element is unexpected.
    """
    try:
        root = etree.fromstring(xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content)
    except etree.XMLSyntaxError as exc:
        raise ValueError(f"Invalid XML: {exc}") from exc

    # Normalise namespace: some documents omit the ubl: prefix on the root
    local = etree.QName(root.tag).localname
    if local != "Invoice":
        raise ValueError(f"Root element is '{local}', expected 'Invoice'")

    # ── Basic fields ──────────────────────────────────────────────────────────
    invoice_number = _text(root, "cbc:ID/text()")
    issue_date_raw = _text(root, "cbc:IssueDate/text()")
    due_date_raw = _text(root, "cac:PaymentMeans/cbc:PaymentDueDate/text()") or \
                   _text(root, "cbc:DueDate/text()")
    invoice_type = _text(root, "cbc:InvoiceTypeCode/text()")
    currency = _text(root, "cbc:DocumentCurrencyCode/text()")

    # ── Supplier ─────────────────────────────────────────────────────────────
    supplier_party_el = root.xpath("cac:AccountingSupplierParty/cac:Party", namespaces=NS)
    supplier = _parse_party(supplier_party_el[0] if supplier_party_el else None)

    # ── Customer ─────────────────────────────────────────────────────────────
    customer_party_el = root.xpath("cac:AccountingCustomerParty/cac:Party", namespaces=NS)
    customer = _parse_party(customer_party_el[0] if customer_party_el else None)

    # ── IBAN (PaymentMeans → PayeeFinancialAccount) ───────────────────────────
    iban = _text(root, "cac:PaymentMeans/cac:PayeeFinancialAccount/cbc:ID/text()")
    supplier["iban"] = iban

    # ── Monetary totals ───────────────────────────────────────────────────────
    payable_amount = _decimal(root, "cac:LegalMonetaryTotal/cbc:PayableAmount/text()")
    tax_exclusive_amount = _decimal(root, "cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount/text()")
    tax_inclusive_amount = _decimal(root, "cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount/text()")

    # ── Tax total ─────────────────────────────────────────────────────────────
    tax_amount = _decimal(root, "cac:TaxTotal/cbc:TaxAmount/text()")

    # ── Tax subtotals ─────────────────────────────────────────────────────────
    tax_subtotals: list[dict[str, Any]] = []
    for subtotal_el in root.xpath("cac:TaxTotal/cac:TaxSubtotal", namespaces=NS):
        tax_subtotals.append({
            "tax_category": _text(subtotal_el, "cac:TaxCategory/cbc:ID/text()"),
            "tax_percent": _decimal(subtotal_el, "cac:TaxCategory/cbc:Percent/text()"),
            "taxable_amount": _decimal(subtotal_el, "cbc:TaxableAmount/text()"),
            "tax_amount": _decimal(subtotal_el, "cbc:TaxAmount/text()"),
            "tax_exemption_reason_code": _text(subtotal_el, "cac:TaxCategory/cbc:TaxExemptionReasonCode/text()"),
            "tax_exemption_reason": _text(subtotal_el, "cac:TaxCategory/cbc:TaxExemptionReason/text()"),
        })

    # ── Invoice lines ─────────────────────────────────────────────────────────
    invoice_lines: list[dict[str, Any]] = []
    for line_el in root.xpath("cac:InvoiceLine", namespaces=NS):
        price_el = line_el.xpath("cac:Price", namespaces=NS)
        unit_price = _decimal(price_el[0], "cbc:PriceAmount/text()") if price_el else None

        tax_el = line_el.xpath("cac:Item/cac:ClassifiedTaxCategory", namespaces=NS)
        tax_category = _text(tax_el[0], "cbc:ID/text()") if tax_el else None
        tax_percent = _decimal(tax_el[0], "cbc:Percent/text()") if tax_el else None

        invoice_lines.append({
            "line_number": _text(line_el, "cbc:ID/text()"),
            "description": _text(line_el, "cac:Item/cbc:Name/text()") or
                           _text(line_el, "cac:Item/cbc:Description/text()"),
            "quantity": _decimal(line_el, "cbc:InvoicedQuantity/text()"),
            "unit_price": unit_price,
            "line_amount": _decimal(line_el, "cbc:LineExtensionAmount/text()"),
            "tax_category": tax_category,
            "tax_percent": tax_percent,
            "note": _text(line_el, "cbc:Note/text()"),
            "accounting_cost": _text(line_el, "cbc:AccountingCost/text()"),
            "item_name": _text(line_el, "cac:Item/cbc:Name/text()"),
            "buyers_item_id": _text(line_el, "cac:Item/cac:BuyersItemIdentification/cbc:ID/text()"),
            "sellers_item_id": _text(line_el, "cac:Item/cac:SellersItemIdentification/cbc:ID/text()"),
            "standard_item_id": _text(line_el, "cac:Item/cac:StandardItemIdentification/cbc:ID/text()"),
            "item_origin_country": _text(line_el, "cac:Item/cac:OriginCountry/cbc:IdentificationCode/text()"),
            "commodity_classification_code": _text(line_el, "cac:Item/cac:CommodityClassification/cbc:ItemClassificationCode/text()"),
            "invoice_period_start": _text(line_el, "cac:InvoicePeriod/cbc:StartDate/text()"),
            "invoice_period_end": _text(line_el, "cac:InvoicePeriod/cbc:EndDate/text()"),
            "order_line_reference_id": _text(line_el, "cac:OrderLineReference/cbc:LineID/text()"),
            "price_base_quantity": _decimal(line_el, "cac:Price/cbc:BaseQuantity/text()"),
            "tax_exemption_reason": _text(line_el, "cac:Item/cac:ClassifiedTaxCategory/cbc:TaxExemptionReason/text()"),
            "tax_exemption_reason_code": _text(line_el, "cac:Item/cac:ClassifiedTaxCategory/cbc:TaxExemptionReasonCode/text()"),
        })

    return {
        "invoice_number": invoice_number,
        "issue_date": issue_date_raw,
        "due_date": due_date_raw,
        "invoice_type": invoice_type,
        "currency": currency,
        "supplier": supplier,
        "customer": customer,
        "payable_amount": payable_amount,
        "tax_amount": tax_amount,
        "tax_exclusive_amount": tax_exclusive_amount,
        "tax_inclusive_amount": tax_inclusive_amount,
        "tax_subtotals": tax_subtotals,
        "invoice_lines": invoice_lines,
        # UBL header metadata
        "customization_id": _text(root, "cbc:CustomizationID/text()"),
        "profile_id": _text(root, "cbc:ProfileID/text()"),
        "note": _text(root, "cbc:Note/text()"),
        "tax_point_date": _text(root, "cbc:TaxPointDate/text()"),
        "tax_currency_code": _text(root, "cbc:TaxCurrencyCode/text()"),
        "accounting_cost": _text(root, "cbc:AccountingCost/text()"),
        "buyer_reference": _text(root, "cbc:BuyerReference/text()"),
        # Period
        "invoice_period_start": _text(root, "cac:InvoicePeriod/cbc:StartDate/text()"),
        "invoice_period_end": _text(root, "cac:InvoicePeriod/cbc:EndDate/text()"),
        "invoice_period_description_code": _text(root, "cac:InvoicePeriod/cbc:DescriptionCode/text()"),
        # References
        "order_reference_id": _text(root, "cac:OrderReference/cbc:ID/text()"),
        "sales_order_id": _text(root, "cac:OrderReference/cbc:SalesOrderID/text()"),
        "billing_reference_id": _text(root, "cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID/text()"),
        "despatch_document_reference_id": _text(root, "cac:DespatchDocumentReference/cbc:ID/text()"),
        "receipt_document_reference_id": _text(root, "cac:ReceiptDocumentReference/cbc:ID/text()"),
        "contract_document_reference_id": _text(root, "cac:ContractDocumentReference/cbc:ID/text()"),
        "project_reference_id": _text(root, "cac:ProjectReference/cbc:ID/text()"),
        # Delivery
        "delivery_actual_delivery_date": _text(root, "cac:Delivery/cbc:ActualDeliveryDate/text()"),
        "delivery_location_id": _text(root, "cac:Delivery/cac:DeliveryLocation/cbc:ID/text()"),
        "delivery_street_name": _text(root, "cac:Delivery/cac:DeliveryLocation/cac:Address/cbc:StreetName/text()"),
        "delivery_city_name": _text(root, "cac:Delivery/cac:DeliveryLocation/cac:Address/cbc:CityName/text()"),
        "delivery_postal_zone": _text(root, "cac:Delivery/cac:DeliveryLocation/cac:Address/cbc:PostalZone/text()"),
        "delivery_country_code": _text(root, "cac:Delivery/cac:DeliveryLocation/cac:Address/cac:Country/cbc:IdentificationCode/text()"),
        "delivery_party_name": _text(root, "cac:Delivery/cac:DeliveryParty/cac:PartyName/cbc:Name/text()"),
        # Payment
        "payment_means_code": _text(root, "cac:PaymentMeans/cbc:PaymentMeansCode/text()"),
        "payment_means_payment_id": _text(root, "cac:PaymentMeans/cbc:PaymentID/text()"),
        "payment_means_iban": _text(root, "cac:PaymentMeans/cac:PayeeFinancialAccount/cbc:ID/text()"),
        "payment_means_swift": _text(root, "cac:PaymentMeans/cac:PayeeFinancialAccount/cac:FinancialInstitutionBranch/cbc:ID/text()"),
        "payment_terms_note": _text(root, "cac:PaymentTerms/cbc:Note/text()"),
        # Monetary totals extras
        "allowance_total_amount": _decimal(root, "cac:LegalMonetaryTotal/cbc:AllowanceTotalAmount/text()"),
        "charge_total_amount": _decimal(root, "cac:LegalMonetaryTotal/cbc:ChargeTotalAmount/text()"),
        "prepaid_amount": _decimal(root, "cac:LegalMonetaryTotal/cbc:PrepaidAmount/text()"),
        "payable_rounding_amount": _decimal(root, "cac:LegalMonetaryTotal/cbc:PayableRoundingAmount/text()"),
        "line_extension_amount": _decimal(root, "cac:LegalMonetaryTotal/cbc:LineExtensionAmount/text()"),
    }
