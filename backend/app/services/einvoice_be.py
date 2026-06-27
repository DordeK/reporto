"""
e-invoice.be Peppol Access Point API client.
Base URL staging: https://api-dev.e-invoice.be
Base URL production: https://api.e-invoice.be
Auth: Bearer token via Authorization header
"""
import httpx
from app.config import settings


def _base_url() -> str:
    if settings.EINVOICE_BE_ENV == "production":
        return "https://api.e-invoice.be"
    return "https://api-dev.e-invoice.be"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.EINVOICE_BE_API_KEY}",
    }


async def check_connection() -> dict:
    """Verify API key by calling GET /api/me/"""
    if not settings.EINVOICE_BE_API_KEY:
        return {"connected": False, "error": "EINVOICE_BE_API_KEY not configured"}
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{_base_url()}/api/me/", headers=_headers(), timeout=10.0)
            if r.status_code == 200:
                return {"connected": True, "account": r.json()}
            return {"connected": False, "error": f"HTTP {r.status_code}: {r.text}"}
        except Exception as e:
            return {"connected": False, "error": str(e)}


async def list_inbox_invoices(page: int = 1, page_size: int = 50) -> dict:
    """
    Fetch received invoices from GET /api/inbox/invoices
    Returns paginated response with DocumentResponse items.
    """
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_base_url()}/api/inbox/invoices",
            headers=_headers(),
            params={"page": page, "page_size": page_size},
            timeout=30.0,
        )
        r.raise_for_status()
        return r.json()


async def get_document_ubl(document_id: str) -> str:
    """Fetch raw UBL XML for a document via GET /api/documents/{id}/ubl"""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_base_url()}/api/documents/{document_id}/ubl",
            headers={**_headers(), "Accept": "application/xml"},
            timeout=30.0,
        )
        r.raise_for_status()
        return r.text


def build_json_payload(data: dict) -> dict:
    """
    Convert our internal invoice form data to the e-invoice.be DocumentCreate schema.
    Ref: POST /api/documents/ in docs/api-1.json
    """
    supplier = data.get("supplier", {})
    customer = data.get("customer", {})

    payload: dict = {
        "document_type": "INVOICE",
        "invoice_id": data.get("invoice_number", "INV-001"),
        "invoice_date": data.get("issue_date", ""),
        "currency": data.get("currency", "EUR"),
        "vendor_name": supplier.get("name", ""),
        "vendor_tax_id": supplier.get("vat_id") or None,
        "customer_name": customer.get("name", ""),
        "customer_tax_id": customer.get("vat_id") or None,
        "items": [
            {
                "description": ln.get("description", ""),
                "quantity": ln.get("quantity", 1),
                "unit_price": ln.get("unit_price", 0),
                "tax_rate": str(float(ln.get("tax_percent", 21))),
            }
            for ln in data.get("lines", [])
        ],
    }

    if data.get("due_date"):
        payload["due_date"] = data["due_date"]
    if data.get("note"):
        payload["note"] = data["note"]
    if data.get("buyer_reference"):
        payload["purchase_order"] = data["buyer_reference"]
    if data.get("payment_terms_note"):
        payload["payment_term"] = data["payment_terms_note"]
    if supplier.get("iban"):
        payload["payment_details"] = [{"iban": supplier["iban"]}]
    if customer.get("contact_email"):
        payload["customer_email"] = customer["contact_email"]
    if supplier.get("contact_email"):
        payload["vendor_email"] = supplier["contact_email"]

    return payload


async def send_outbox_invoice(data: dict, ubl_xml: str) -> dict:
    """
    Two-step workflow per e-invoice.be API (docs/api-1.json):
      1. POST /api/documents/ubl — upload UBL XML (routing derived from XML EndpointIDs)
      2. POST /api/documents/{id}/send — deliver via Peppol

    `data` is the raw form payload; `ubl_xml` is the already-built UBL 2.1 XML string.
    Returns the send response dict (includes 'id', 'state', etc.).
    """
    if not settings.EINVOICE_BE_API_KEY:
        raise ValueError("EINVOICE_BE_API_KEY not configured")

    async with httpx.AsyncClient() as client:
        # Step 1: create document via UBL upload (API extracts routing from XML)
        create_resp = await client.post(
            f"{_base_url()}/api/documents/ubl",
            headers=_headers(),
            files={"file": ("invoice.xml", ubl_xml.encode("utf-8"), "application/xml")},
            timeout=30.0,
        )
        if not create_resp.is_success:
            raise ValueError(
                f"HTTP {create_resp.status_code} on POST /api/documents/ubl: {create_resp.text}"
            )
        doc = create_resp.json()
        doc_id = doc["id"]

        # Step 2: send via Peppol — pass routing explicitly as query params
        send_params: dict[str, str] = {}
        for role, party_key in [("sender", "supplier"), ("receiver", "customer")]:
            endpoint = data.get(party_key, {}).get("endpoint_id", "")
            if endpoint and ":" in endpoint:
                scheme, pid = endpoint.split(":", 1)
                send_params[f"{role}_peppol_scheme"] = scheme
                send_params[f"{role}_peppol_id"] = pid

        send_resp = await client.post(
            f"{_base_url()}/api/documents/{doc_id}/send",
            headers=_headers(),
            params=send_params,
            timeout=30.0,
        )
        if not send_resp.is_success:
            raise ValueError(
                f"HTTP {send_resp.status_code} on POST /api/documents/{doc_id}/send: {send_resp.text}"
            )
        result = send_resp.json()
        result["id"] = doc_id
        return result
