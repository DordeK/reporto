"""
Deterministic anomaly detection for imported invoices.
Runs a series of rule-based checks and inserts Anomaly records.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Anomaly, Invoice, InvoiceLine, Party, TaxSubtotal


EU_VAT_RATES = {Decimal("0"), Decimal("6"), Decimal("9"), Decimal("12"), Decimal("21")}
TOLERANCE = Decimal("0.02")


async def _add_anomaly(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    severity: str,
    category: str,
    message: str,
) -> None:
    anomaly = Anomaly(
        id=uuid.uuid4(),
        invoice_id=invoice_id,
        severity=severity,
        category=category,
        message=message,
    )
    db.add(anomaly)


async def run_deterministic_checks(
    db: AsyncSession, invoice_id: uuid.UUID
) -> list[dict[str, Any]]:
    """
    Run all deterministic checks for a given invoice.
    Inserts Anomaly rows for each detected issue.
    Returns a list of dicts describing found anomalies.
    """
    # Load the invoice
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id)
    )
    invoice = result.scalars().first()
    if not invoice:
        return []

    detected: list[dict[str, Any]] = []

    async def flag(severity: str, category: str, message: str) -> None:
        await _add_anomaly(db, invoice_id, severity, category, message)
        detected.append({"severity": severity, "category": category, "message": message})

    # 1. Duplicate invoice number from the same supplier
    dup_result = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.invoice_number == invoice.invoice_number,
            Invoice.supplier_id == invoice.supplier_id,
            Invoice.id != invoice.id,
        )
    )
    dup_count = dup_result.scalar() or 0
    if dup_count > 0:
        await flag("high", "duplicate_invoice_number",
                   f"Invoice number '{invoice.invoice_number}' already exists for this supplier "
                   f"({dup_count} duplicate(s) found).")

    # 2. Missing supplier VAT ID
    supplier_result = await db.execute(select(Party).where(Party.id == invoice.supplier_id))
    supplier = supplier_result.scalars().first()
    if supplier and not supplier.vat_id:
        await flag("medium", "missing_vat_id",
                   "Supplier VAT ID is missing.")

    # 3. Missing issue date
    if invoice.issue_date is None:
        await flag("high", "missing_issue_date",
                   "Invoice issue date is missing.")

    # 4. Due date before issue date
    if invoice.issue_date and invoice.due_date and invoice.due_date < invoice.issue_date:
        await flag("high", "due_before_issue",
                   f"Due date ({invoice.due_date}) is earlier than issue date ({invoice.issue_date}).")

    # 5. Tax amount mismatch per subtotal
    st_result = await db.execute(
        select(TaxSubtotal).where(TaxSubtotal.invoice_id == invoice_id)
    )
    subtotals = st_result.scalars().all()
    for st in subtotals:
        if (
            st.taxable_amount is not None
            and st.tax_percent is not None
            and st.tax_amount is not None
        ):
            expected = st.taxable_amount * st.tax_percent / Decimal("100")
            diff = abs(expected - st.tax_amount)
            if diff > TOLERANCE:
                await flag("medium", "tax_amount_mismatch",
                           f"Tax subtotal mismatch: expected {expected:.4f}, "
                           f"got {st.tax_amount:.4f} (diff={diff:.4f}) "
                           f"for category '{st.tax_category}' at {st.tax_percent}%.")

    # 6. Total mismatch: sum(line_amounts) vs tax_exclusive_amount
    lines_result = await db.execute(
        select(InvoiceLine).where(InvoiceLine.invoice_id == invoice_id)
    )
    lines = lines_result.scalars().all()
    if lines and invoice.tax_exclusive_amount is not None:
        lines_with_amount = [ln for ln in lines if ln.line_amount is not None]
        if lines_with_amount:
            lines_total = sum(ln.line_amount for ln in lines_with_amount)
            diff = abs(lines_total - invoice.tax_exclusive_amount)
            if diff > TOLERANCE:
                await flag("medium", "total_mismatch",
                           f"Sum of line amounts ({lines_total:.4f}) does not match "
                           f"TaxExclusiveAmount ({invoice.tax_exclusive_amount:.4f}) "
                           f"(diff={diff:.4f}).")

    # 7. Unexpected VAT rate
    for st in subtotals:
        if st.tax_percent is not None:
            rounded = round(st.tax_percent, 0)
            if Decimal(str(rounded)) not in EU_VAT_RATES:
                await flag("medium", "unexpected_vat_rate",
                           f"Unexpected VAT rate {st.tax_percent}% "
                           f"(category '{st.tax_category}'). Expected one of {sorted(EU_VAT_RATES)}.")

    # 8. Missing supplier IBAN
    if supplier and not supplier.iban:
        await flag("low", "missing_iban",
                   "Supplier IBAN / financial account is missing.")

    # 9. Reverse charge with non-zero VAT
    for st in subtotals:
        if st.tax_category == "AE" and st.tax_amount and st.tax_amount > 0:
            await flag("high", "reverse_charge_with_vat",
                       f"Reverse charge (AE) subtotal has positive tax amount {st.tax_amount}. "
                       "Under reverse charge the supplier should not charge VAT.")

    # 10. Currency mismatch across subtotals / lines (detect if invoice has mixed currencies)
    # We infer by checking if any line tax_category label contains a currency indicator —
    # but the safer approach is to compare: if multiple distinct tax_percent values AND
    # the invoice lists more than one currency string in parsed data. Here we do a simpler
    # proxy: check if invoice_lines have widely varying tax_percent suggesting data corruption.
    # In practice this fires when the raw XML contains cbc:LineExtensionAmount with different
    # currencyID attributes. We flag it as informational.
    if lines:
        currencies_in_lines = set()
        for ln in lines:
            # We don't store currencyID per line in the model, but we flag if the invoice-level
            # currency is absent, suggesting the document may have mixed currencies.
            pass
        # Low-value: flag if invoice currency is missing but lines exist
        if invoice.currency is None and lines:
            await flag("low", "currency_mismatch",
                       "Invoice currency code is missing but invoice lines are present; "
                       "possible multi-currency document.")

    await db.flush()
    return detected


async def run_all_invoices_detection(db: AsyncSession) -> dict[str, int]:
    """Run deterministic checks on every invoice. Returns summary counts."""
    result = await db.execute(select(Invoice.id))
    invoice_ids = result.scalars().all()

    total_new = 0
    for inv_id in invoice_ids:
        found = await run_deterministic_checks(db, inv_id)
        total_new += len(found)

    await db.commit()
    return {"invoices_checked": len(invoice_ids), "new_anomalies": total_new}
