"""
Invoice ingestion service.
Handles deduplication, party upsert, invoice + lines + subtotals insertion,
and triggers anomaly detection after each successful import.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Invoice, InvoiceLine, Party, RawInvoiceFile, TaxSubtotal
from app.services.ubl_parser import parse_ubl


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except (ValueError, TypeError):
        return None


async def _upsert_party(db: AsyncSession, party_data: dict[str, Any]) -> Party:
    """
    Upsert a party by vat_id (if present). Otherwise always insert a new row
    so that nameless / vat-less counterparties do not collide.
    """
    vat_id = party_data.get("vat_id")
    if vat_id:
        result = await db.execute(select(Party).where(Party.vat_id == vat_id))
        existing = result.scalars().first()
        if existing:
            # Update fields that may have been enriched
            existing.name = party_data.get("name") or existing.name
            existing.country_code = party_data.get("country_code") or existing.country_code
            existing.endpoint_id = party_data.get("endpoint_id") or existing.endpoint_id
            existing.iban = party_data.get("iban") or existing.iban
            existing.street_name = party_data.get("street_name") or existing.street_name
            existing.additional_street_name = party_data.get("additional_street_name") or existing.additional_street_name
            existing.city_name = party_data.get("city_name") or existing.city_name
            existing.postal_zone = party_data.get("postal_zone") or existing.postal_zone
            existing.country_subentity = party_data.get("country_subentity") or existing.country_subentity
            existing.registration_name = party_data.get("registration_name") or existing.registration_name
            existing.company_id = party_data.get("company_id") or existing.company_id
            existing.company_legal_form = party_data.get("company_legal_form") or existing.company_legal_form
            existing.contact_name = party_data.get("contact_name") or existing.contact_name
            existing.contact_telephone = party_data.get("contact_telephone") or existing.contact_telephone
            existing.contact_email = party_data.get("contact_email") or existing.contact_email
            existing.endpoint_scheme = party_data.get("endpoint_scheme") or existing.endpoint_scheme
            return existing

    party = Party(
        id=uuid.uuid4(),
        name=party_data.get("name"),
        vat_id=vat_id,
        country_code=party_data.get("country_code"),
        endpoint_id=party_data.get("endpoint_id"),
        iban=party_data.get("iban"),
        street_name=party_data.get("street_name"),
        additional_street_name=party_data.get("additional_street_name"),
        city_name=party_data.get("city_name"),
        postal_zone=party_data.get("postal_zone"),
        country_subentity=party_data.get("country_subentity"),
        registration_name=party_data.get("registration_name"),
        company_id=party_data.get("company_id"),
        company_legal_form=party_data.get("company_legal_form"),
        contact_name=party_data.get("contact_name"),
        contact_telephone=party_data.get("contact_telephone"),
        contact_email=party_data.get("contact_email"),
        endpoint_scheme=party_data.get("endpoint_scheme"),
    )
    db.add(party)
    return party


async def ingest_xml(
    db: AsyncSession,
    xml_content: str,
    source: str,
    filename: str | None = None,
) -> dict[str, Any]:
    """
    Full ingestion pipeline for a single UBL XML invoice string.

    Returns:
        dict with keys:
          - invoice_id (UUID | None)
          - status: "imported" | "duplicate" | "error"
          - error (str, only on error)
    """
    # 1. Compute hash for deduplication
    content_hash = _sha256(xml_content)

    # 2. Check duplicate
    result = await db.execute(
        select(RawInvoiceFile).where(RawInvoiceFile.content_hash == content_hash)
    )
    existing_raw = result.scalars().first()
    if existing_raw:
        existing_invoice = await db.execute(
            select(Invoice).where(Invoice.raw_file_id == existing_raw.id)
        )
        inv = existing_invoice.scalars().first()
        return {
            "invoice_id": str(inv.id) if inv else None,
            "status": "duplicate",
        }

    # 3. Parse XML
    try:
        parsed = parse_ubl(xml_content)
    except ValueError as exc:
        return {"invoice_id": None, "status": "error", "error": str(exc)}

    # 4. Insert raw file
    raw_file = RawInvoiceFile(
        id=uuid.uuid4(),
        source=source,
        filename=filename,
        content=xml_content,
        content_hash=content_hash,
    )
    db.add(raw_file)
    await db.flush()  # obtain raw_file.id

    # 5. Upsert supplier
    supplier = await _upsert_party(db, parsed["supplier"])
    await db.flush()

    # 6. Upsert customer
    customer = await _upsert_party(db, parsed["customer"])
    await db.flush()

    # 7. Insert invoice
    invoice = Invoice(
        id=uuid.uuid4(),
        raw_file_id=raw_file.id,
        invoice_number=parsed["invoice_number"] or "UNKNOWN",
        invoice_type=parsed.get("invoice_type"),
        direction="received",
        issue_date=_parse_date(parsed.get("issue_date")),
        due_date=_parse_date(parsed.get("due_date")),
        currency=parsed.get("currency"),
        supplier_id=supplier.id,
        customer_id=customer.id,
        payable_amount=parsed.get("payable_amount"),
        tax_amount=parsed.get("tax_amount"),
        tax_exclusive_amount=parsed.get("tax_exclusive_amount"),
        tax_inclusive_amount=parsed.get("tax_inclusive_amount"),
        # UBL header metadata
        customization_id=parsed.get("customization_id"),
        profile_id=parsed.get("profile_id"),
        note=parsed.get("note"),
        tax_point_date=_parse_date(parsed.get("tax_point_date")),
        tax_currency_code=parsed.get("tax_currency_code"),
        accounting_cost=parsed.get("accounting_cost"),
        buyer_reference=parsed.get("buyer_reference"),
        # Invoice period
        invoice_period_start=_parse_date(parsed.get("invoice_period_start")),
        invoice_period_end=_parse_date(parsed.get("invoice_period_end")),
        invoice_period_description_code=parsed.get("invoice_period_description_code"),
        # References
        order_reference_id=parsed.get("order_reference_id"),
        sales_order_id=parsed.get("sales_order_id"),
        billing_reference_id=parsed.get("billing_reference_id"),
        billing_reference_issue_date=_parse_date(parsed.get("billing_reference_issue_date")),
        despatch_document_reference_id=parsed.get("despatch_document_reference_id"),
        receipt_document_reference_id=parsed.get("receipt_document_reference_id"),
        originator_document_reference_id=parsed.get("originator_document_reference_id"),
        contract_document_reference_id=parsed.get("contract_document_reference_id"),
        project_reference_id=parsed.get("project_reference_id"),
        # Delivery
        delivery_actual_delivery_date=_parse_date(parsed.get("delivery_actual_delivery_date")),
        delivery_location_id=parsed.get("delivery_location_id"),
        delivery_street_name=parsed.get("delivery_street_name"),
        delivery_city_name=parsed.get("delivery_city_name"),
        delivery_postal_zone=parsed.get("delivery_postal_zone"),
        delivery_country_code=parsed.get("delivery_country_code"),
        delivery_party_name=parsed.get("delivery_party_name"),
        # Payment means
        payment_means_code=parsed.get("payment_means_code"),
        payment_means_payment_id=parsed.get("payment_means_payment_id"),
        payment_means_iban=parsed.get("payment_means_iban"),
        payment_means_swift=parsed.get("payment_means_swift"),
        payment_terms_note=parsed.get("payment_terms_note"),
        # Monetary totals extras
        allowance_total_amount=parsed.get("allowance_total_amount"),
        charge_total_amount=parsed.get("charge_total_amount"),
        prepaid_amount=parsed.get("prepaid_amount"),
        payable_rounding_amount=parsed.get("payable_rounding_amount"),
        line_extension_amount=parsed.get("line_extension_amount"),
    )
    db.add(invoice)
    await db.flush()

    # 8. Insert invoice lines
    for line_data in parsed.get("invoice_lines", []):
        line = InvoiceLine(
            id=uuid.uuid4(),
            invoice_id=invoice.id,
            line_number=line_data.get("line_number"),
            description=line_data.get("description"),
            quantity=line_data.get("quantity"),
            unit_price=line_data.get("unit_price"),
            line_amount=line_data.get("line_amount"),
            tax_category=line_data.get("tax_category"),
            tax_percent=line_data.get("tax_percent"),
            note=line_data.get("note"),
            accounting_cost=line_data.get("accounting_cost"),
            item_name=line_data.get("item_name"),
            buyers_item_id=line_data.get("buyers_item_id"),
            sellers_item_id=line_data.get("sellers_item_id"),
            standard_item_id=line_data.get("standard_item_id"),
            item_origin_country=line_data.get("item_origin_country"),
            commodity_classification_code=line_data.get("commodity_classification_code"),
            invoice_period_start=_parse_date(line_data.get("invoice_period_start")),
            invoice_period_end=_parse_date(line_data.get("invoice_period_end")),
            order_line_reference_id=line_data.get("order_line_reference_id"),
            price_base_quantity=line_data.get("price_base_quantity"),
            tax_exemption_reason=line_data.get("tax_exemption_reason"),
            tax_exemption_reason_code=line_data.get("tax_exemption_reason_code"),
        )
        db.add(line)

    # 9. Insert tax subtotals
    for st_data in parsed.get("tax_subtotals", []):
        subtotal = TaxSubtotal(
            id=uuid.uuid4(),
            invoice_id=invoice.id,
            tax_category=st_data.get("tax_category"),
            tax_percent=st_data.get("tax_percent"),
            taxable_amount=st_data.get("taxable_amount"),
            tax_amount=st_data.get("tax_amount"),
            tax_exemption_reason_code=st_data.get("tax_exemption_reason_code"),
            tax_exemption_reason=st_data.get("tax_exemption_reason"),
        )
        db.add(subtotal)

    await db.flush()

    # 10. Run anomaly detection
    # Import here to avoid circular dependency
    from app.services.anomaly_service import run_deterministic_checks
    await run_deterministic_checks(db, invoice.id)

    await db.commit()

    return {"invoice_id": str(invoice.id), "status": "imported"}
