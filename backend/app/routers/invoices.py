"""
Invoice ingestion and retrieval endpoints.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.models import Anomaly, Invoice, Party, RawInvoiceFile
from app.schemas.invoice import (
    InvoiceDetail,
    InvoiceListItem,
    UploadResponse,
)
from app.services.ingestion import ingest_xml
from app.services import audit_service

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /invoices/send
# ---------------------------------------------------------------------------

@router.post("/send")
async def send_invoice(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Compose a UBL 2.1 invoice, optionally send it via Peppol (e-invoice.be),
    and store it in the database as direction='sent'.

    Body fields:
      invoice_number, issue_date, due_date, currency,
      supplier: {name, vat_id, street_name, city_name, postal_zone, country_code,
                  endpoint_id, iban, contact_email},
      customer: {name, vat_id, street_name, city_name, postal_zone, country_code,
                  endpoint_id},
      lines: [{description, quantity, unit_price, tax_percent, tax_category}],
      note, payment_terms_note, buyer_reference,
      send_via_peppol: bool (default true)
    """
    from app.services.ubl_builder import build_ubl_invoice
    from app.services import einvoice_be, audit_service

    actor = request.headers.get("X-User-Id", "anonymous")
    ip = request.client.host if request.client else None

    # 1. Build UBL XML
    try:
        ubl_xml = build_ubl_invoice(body)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"UBL build failed: {exc}")

    # 2. Optionally send via Peppol
    peppol_response: dict | None = None
    peppol_error: str | None = None
    send_via_peppol = body.get("send_via_peppol", True)

    if send_via_peppol and settings.EINVOICE_BE_API_KEY:
        try:
            peppol_response = await einvoice_be.send_outbox_invoice(body, ubl_xml)
        except Exception as exc:
            peppol_error = str(exc)

    # 3. Ingest into DB as direction='sent'
    result = await ingest_xml(db, ubl_xml, source="sent", filename=f"{body.get('invoice_number', 'invoice')}.xml")

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error", "Ingestion failed"))

    # 4. Tag as sent + store peppol metadata
    if result.get("invoice_id"):
        from sqlalchemy import select as sa_select
        inv_result = await db.execute(sa_select(Invoice).where(Invoice.id == uuid.UUID(result["invoice_id"])))
        inv = inv_result.scalar_one_or_none()
        if inv:
            inv.direction = "sent"
            if peppol_response:
                inv.peppol_document_id = peppol_response.get("id")
                inv.peppol_state = peppol_response.get("state")
            await db.flush()

    await db.commit()

    await audit_service.log_action(
        db, action="invoice.send",
        entity_type="invoice", entity_id=result.get("invoice_id"),
        actor=actor, ip_address=ip,
        details={
            "invoice_number": body.get("invoice_number"),
            "customer": body.get("customer", {}).get("name"),
            "peppol_sent": peppol_response is not None,
            "peppol_error": peppol_error,
        },
    )
    await db.commit()

    return {
        "invoice_id": result.get("invoice_id"),
        "status": result["status"],
        "ubl_xml": ubl_xml,
        "peppol": peppol_response,
        "peppol_error": peppol_error,
    }


# ---------------------------------------------------------------------------
# POST /invoices/upload
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse)
async def upload_invoices(
    request: Request,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Accept multiple UBL XML files and ingest them."""
    imported = 0
    duplicates = 0
    errors = 0
    details: list[dict] = []

    actor = request.headers.get("X-User-Id", "anonymous")
    ip = request.client.host if request.client else None

    for upload in files:
        try:
            raw_bytes = await upload.read()
            xml_content = raw_bytes.decode("utf-8", errors="replace")
            result = await ingest_xml(
                db,
                xml_content,
                source="upload",
                filename=upload.filename,
            )
            if result["status"] == "imported":
                imported += 1
            elif result["status"] == "duplicate":
                duplicates += 1
            else:
                errors += 1
            details.append({"filename": upload.filename, **result})
        except Exception as exc:
            errors += 1
            details.append({"filename": upload.filename, "status": "error", "error": str(exc)})

    await audit_service.log_action(
        db,
        action="invoice.upload",
        actor=actor,
        ip_address=ip,
        details={"imported": imported, "duplicates": duplicates, "errors": errors, "files": [d.get("filename") for d in details]},
    )
    await db.commit()

    return UploadResponse(imported=imported, duplicates=duplicates, errors=errors, details=details)


# ---------------------------------------------------------------------------
# POST /invoices/ingest-provider
# ---------------------------------------------------------------------------

@router.post("/ingest-provider")
async def ingest_from_provider(request: Request, db: AsyncSession = Depends(get_db)):
    from app.services import einvoice_be, audit_service

    # Check API key configured
    if not settings.EINVOICE_BE_API_KEY:
        raise HTTPException(status_code=503, detail="EINVOICE_BE_API_KEY not configured. Add it to your .env file.")

    actor = request.headers.get("X-User-Id", "anonymous")
    ip = request.client.host if request.client else None

    total_new = 0
    total_duplicates = 0
    total_errors = 0
    details_list = []

    # Paginate through all inbox invoices
    page = 1
    while True:
        try:
            resp = await einvoice_be.list_inbox_invoices(page=page, page_size=50)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"e-invoice.be API error: {str(e)}")

        items = resp.get("items", resp) if isinstance(resp, dict) else resp
        if not items:
            break

        for doc in items:
            doc_id = doc.get("id")
            if not doc_id:
                continue

            # Check if already imported by peppol_document_id
            existing = await db.execute(
                select(Invoice).where(Invoice.peppol_document_id == doc_id)
            )
            if existing.scalar_one_or_none():
                total_duplicates += 1
                details_list.append({"peppol_id": doc_id, "status": "duplicate"})
                continue

            try:
                ubl_xml = await einvoice_be.get_document_ubl(doc_id)
                result = await ingest_xml(
                    db=db,
                    xml_content=ubl_xml,
                    source="peppol",
                    filename=f"{doc_id}.xml",
                )
                if result["status"] == "duplicate":
                    total_duplicates += 1
                    details_list.append({"peppol_id": doc_id, "status": "duplicate"})
                else:
                    # Update peppol-specific fields on the newly created invoice
                    if result.get("invoice_id"):
                        inv_result = await db.execute(
                            select(Invoice).where(Invoice.id == uuid.UUID(result["invoice_id"]))
                        )
                        inv = inv_result.scalar_one_or_none()
                        if inv:
                            inv.peppol_document_id = doc_id
                            inv.peppol_state = doc.get("state")
                            inv.peppol_sender_id = doc.get("vendor_tax_id")
                            inv.peppol_receiver_id = doc.get("customer_tax_id")
                            inv.direction = "received"
                            await db.flush()
                    total_new += 1
                    details_list.append({"peppol_id": doc_id, "status": "imported", "invoice_id": result.get("invoice_id")})
            except Exception as e:
                total_errors += 1
                details_list.append({"peppol_id": doc_id, "status": "error", "error": str(e)})

        # Check if there are more pages
        if isinstance(resp, dict):
            total_pages = resp.get("total_pages", 1)
            if page >= total_pages:
                break
        else:
            break
        page += 1

    await db.commit()

    await audit_service.log_action(
        db, action="invoice.sync_peppol",
        actor=actor, ip_address=ip,
        details={"new": total_new, "duplicates": total_duplicates, "errors": total_errors}
    )
    await db.commit()

    return {"synced": total_new + total_duplicates, "new": total_new, "duplicates": total_duplicates, "errors": total_errors, "details": details_list}


# ---------------------------------------------------------------------------
# GET /invoices/provider/status
# ---------------------------------------------------------------------------

@router.get("/provider/status")
async def get_provider_status():
    from app.services import einvoice_be
    return await einvoice_be.check_connection()


# ---------------------------------------------------------------------------
# GET /invoices
# ---------------------------------------------------------------------------

@router.get("", response_model=dict)
async def list_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    direction: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Return a paginated list of invoices with key fields."""
    offset = (page - 1) * limit

    # Build base query with joins for supplier/customer names and anomaly count
    from sqlalchemy import case, literal, outerjoin
    from sqlalchemy.orm import aliased

    SupplierParty = aliased(Party, name="supplier")
    CustomerParty = aliased(Party, name="customer")

    query = (
        select(
            Invoice,
            SupplierParty.name.label("supplier_name"),
            CustomerParty.name.label("customer_name"),
            RawInvoiceFile.source.label("source"),
            func.count(Anomaly.id).label("anomaly_count"),
        )
        .join(SupplierParty, Invoice.supplier_id == SupplierParty.id)
        .join(CustomerParty, Invoice.customer_id == CustomerParty.id)
        .join(RawInvoiceFile, Invoice.raw_file_id == RawInvoiceFile.id)
        .outerjoin(Anomaly, Anomaly.invoice_id == Invoice.id)
        .group_by(Invoice.id, SupplierParty.name, CustomerParty.name, RawInvoiceFile.source)
        .order_by(Invoice.created_at.desc())
    )

    if direction:
        query = query.where(Invoice.direction == direction)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            Invoice.invoice_number.ilike(search_term) |
            SupplierParty.name.ilike(search_term) |
            CustomerParty.name.ilike(search_term)
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        inv = row.Invoice
        items.append({
            "id": str(inv.id),
            "invoice_number": inv.invoice_number,
            "invoice_type": inv.invoice_type,
            "direction": inv.direction,
            "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
            "due_date": inv.due_date.isoformat() if inv.due_date else None,
            "currency": inv.currency,
            "payable_amount": float(inv.payable_amount) if inv.payable_amount is not None else None,
            "tax_amount": float(inv.tax_amount) if inv.tax_amount is not None else None,
            "supplier_name": row.supplier_name,
            "customer_name": row.customer_name,
            "source": row.source,
            "anomaly_count": row.anomaly_count,
            "created_at": inv.created_at.isoformat(),
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 0,
    }


# ---------------------------------------------------------------------------
# GET /invoices/{invoice_id}
# ---------------------------------------------------------------------------

@router.get("/{invoice_id}", response_model=dict)
async def get_invoice(invoice_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Return full invoice details with lines, tax subtotals, and anomalies."""
    result = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(
            selectinload(Invoice.supplier),
            selectinload(Invoice.customer),
            selectinload(Invoice.lines),
            selectinload(Invoice.tax_subtotals),
            selectinload(Invoice.anomalies),
            selectinload(Invoice.raw_file),
        )
    )
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    def party_dict(p: Party | None) -> dict | None:
        if p is None:
            return None
        return {
            "id": str(p.id),
            "name": p.name,
            "vat_id": p.vat_id,
            "country_code": p.country_code,
            "endpoint_id": p.endpoint_id,
            "iban": p.iban,
        }

    return {
        "id": str(invoice.id),
        "invoice_number": invoice.invoice_number,
        "invoice_type": invoice.invoice_type,
        "direction": invoice.direction,
        "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
        "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        "currency": invoice.currency,
        "payable_amount": float(invoice.payable_amount) if invoice.payable_amount is not None else None,
        "tax_amount": float(invoice.tax_amount) if invoice.tax_amount is not None else None,
        "tax_exclusive_amount": float(invoice.tax_exclusive_amount) if invoice.tax_exclusive_amount is not None else None,
        "tax_inclusive_amount": float(invoice.tax_inclusive_amount) if invoice.tax_inclusive_amount is not None else None,
        "created_at": invoice.created_at.isoformat(),
        "source": invoice.raw_file.source if invoice.raw_file else None,
        "filename": invoice.raw_file.filename if invoice.raw_file else None,
        "supplier": party_dict(invoice.supplier),
        "customer": party_dict(invoice.customer),
        "lines": [
            {
                "id": str(ln.id),
                "line_number": ln.line_number,
                "description": ln.description,
                "quantity": float(ln.quantity) if ln.quantity is not None else None,
                "unit_price": float(ln.unit_price) if ln.unit_price is not None else None,
                "line_amount": float(ln.line_amount) if ln.line_amount is not None else None,
                "tax_category": ln.tax_category,
                "tax_percent": float(ln.tax_percent) if ln.tax_percent is not None else None,
            }
            for ln in invoice.lines
        ],
        "tax_subtotals": [
            {
                "id": str(st.id),
                "tax_category": st.tax_category,
                "tax_percent": float(st.tax_percent) if st.tax_percent is not None else None,
                "taxable_amount": float(st.taxable_amount) if st.taxable_amount is not None else None,
                "tax_amount": float(st.tax_amount) if st.tax_amount is not None else None,
            }
            for st in invoice.tax_subtotals
        ],
        "anomalies": [
            {
                "id": str(a.id),
                "severity": a.severity,
                "category": a.category,
                "message": a.message,
                "detected_at": a.detected_at.isoformat(),
            }
            for a in invoice.anomalies
        ],
    }
