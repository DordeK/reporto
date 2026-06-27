"""
Anomaly retrieval and bulk detection endpoints.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.database import get_db
from app.models.models import Anomaly, Invoice, Party
from app.services.anomaly_service import run_all_invoices_detection

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /anomalies
# ---------------------------------------------------------------------------

@router.get("")
async def list_anomalies(
    severity: Optional[str] = Query(None, description="Filter by severity: high, medium, low"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Return anomalies with joined invoice details."""
    offset = (page - 1) * limit

    SupplierParty = aliased(Party, name="supplier")
    CustomerParty = aliased(Party, name="customer")

    query = (
        select(
            Anomaly,
            Invoice.invoice_number.label("invoice_number"),
            Invoice.currency.label("currency"),
            Invoice.payable_amount.label("payable_amount"),
            Invoice.issue_date.label("issue_date"),
            SupplierParty.name.label("supplier_name"),
            CustomerParty.name.label("customer_name"),
        )
        .outerjoin(Invoice, Anomaly.invoice_id == Invoice.id)
        .outerjoin(SupplierParty, Invoice.supplier_id == SupplierParty.id)
        .outerjoin(CustomerParty, Invoice.customer_id == CustomerParty.id)
        .order_by(Anomaly.detected_at.desc())
    )

    if severity:
        query = query.where(Anomaly.severity == severity)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        a = row.Anomaly
        items.append({
            "id": str(a.id),
            "invoice_id": str(a.invoice_id) if a.invoice_id else None,
            "severity": a.severity,
            "category": a.category,
            "message": a.message,
            "detected_at": a.detected_at.isoformat(),
            "invoice_number": row.invoice_number,
            "currency": row.currency,
            "payable_amount": float(row.payable_amount) if row.payable_amount is not None else None,
            "issue_date": row.issue_date.isoformat() if row.issue_date else None,
            "supplier_name": row.supplier_name,
            "customer_name": row.customer_name,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 0,
    }


# ---------------------------------------------------------------------------
# POST /anomalies/run-detection
# ---------------------------------------------------------------------------

@router.post("/run-detection")
async def run_detection(db: AsyncSession = Depends(get_db)):
    """Re-run deterministic anomaly detection across all invoices."""
    summary = await run_all_invoices_detection(db)
    return {
        "status": "completed",
        **summary,
    }
