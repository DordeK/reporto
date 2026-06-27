"""
Dashboard statistics endpoint.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import Anomaly, Invoice, RawInvoiceFile, ReportRun, TaxSubtotal

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Return aggregated statistics for the dashboard."""

    # ── Invoice counts ────────────────────────────────────────────────────────
    total_result = await db.execute(select(func.count(Invoice.id)))
    total_invoices = total_result.scalar() or 0

    received_result = await db.execute(
        select(func.count(Invoice.id)).where(Invoice.direction == "received")
    )
    received_invoices = received_result.scalar() or 0

    sent_result = await db.execute(
        select(func.count(Invoice.id)).where(Invoice.direction == "sent")
    )
    sent_invoices = sent_result.scalar() or 0

    # ── Financial totals ──────────────────────────────────────────────────────
    vat_result = await db.execute(
        select(func.coalesce(func.sum(Invoice.tax_amount), 0))
    )
    total_vat = float(vat_result.scalar() or 0)

    spend_result = await db.execute(
        select(func.coalesce(func.sum(Invoice.payable_amount), 0))
    )
    total_spend = float(spend_result.scalar() or 0)

    # ── Anomaly counts ────────────────────────────────────────────────────────
    anomaly_result = await db.execute(select(func.count(Anomaly.id)))
    anomaly_count = anomaly_result.scalar() or 0

    high_severity_result = await db.execute(
        select(func.count(Anomaly.id)).where(Anomaly.severity == "high")
    )
    high_severity = high_severity_result.scalar() or 0

    # ── Recent reports ────────────────────────────────────────────────────────
    recent_reports_result = await db.execute(
        select(ReportRun).order_by(ReportRun.created_at.desc()).limit(5)
    )
    recent_reports = recent_reports_result.scalars().all()
    recent_reports_data = [
        {
            "id": str(r.id),
            "user_prompt": r.user_prompt,
            "report_name": r.report_definition.get("reportName", "Unnamed") if r.report_definition else "Unnamed",
            "row_count": (r.result or {}).get("row_count", 0),
            "created_at": r.created_at.isoformat(),
        }
        for r in recent_reports
    ]

    # ── Invoices by source ────────────────────────────────────────────────────
    source_result = await db.execute(
        select(RawInvoiceFile.source, func.count(Invoice.id))
        .join(Invoice, Invoice.raw_file_id == RawInvoiceFile.id)
        .group_by(RawInvoiceFile.source)
    )
    invoices_by_source: dict[str, int] = {row[0]: row[1] for row in source_result.all()}

    # ── VAT by rate ───────────────────────────────────────────────────────────
    vat_by_rate_result = await db.execute(
        select(
            TaxSubtotal.tax_percent,
            func.sum(TaxSubtotal.tax_amount).label("tax_amount"),
            func.sum(TaxSubtotal.taxable_amount).label("taxable_amount"),
        )
        .where(TaxSubtotal.tax_percent.isnot(None))
        .group_by(TaxSubtotal.tax_percent)
        .order_by(TaxSubtotal.tax_percent)
    )
    vat_by_rate = [
        {
            "tax_percent": float(row.tax_percent),
            "tax_amount": float(row.tax_amount) if row.tax_amount is not None else 0.0,
            "taxable_amount": float(row.taxable_amount) if row.taxable_amount is not None else 0.0,
        }
        for row in vat_by_rate_result.all()
    ]

    return {
        "totalInvoices": total_invoices,
        "receivedInvoices": received_invoices,
        "sentInvoices": sent_invoices,
        "totalVat": total_vat,
        "totalSpend": total_spend,
        "anomalyCount": anomaly_count,
        "highSeverityAnomalies": high_severity,
        "recentReports": recent_reports_data,
        "invoicesBySource": invoices_by_source,
        "vatByRate": vat_by_rate,
    }
