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
        "Accept": "application/json",
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
