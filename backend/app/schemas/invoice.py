import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class PartySchema(BaseModel):
    id: uuid.UUID
    name: Optional[str] = None
    vat_id: Optional[str] = None
    country_code: Optional[str] = None
    endpoint_id: Optional[str] = None
    iban: Optional[str] = None

    model_config = {"from_attributes": True}


class InvoiceLineSchema(BaseModel):
    id: uuid.UUID
    line_number: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    line_amount: Optional[Decimal] = None
    tax_category: Optional[str] = None
    tax_percent: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class TaxSubtotalSchema(BaseModel):
    id: uuid.UUID
    tax_category: Optional[str] = None
    tax_percent: Optional[Decimal] = None
    taxable_amount: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None

    model_config = {"from_attributes": True}


class AnomalySchema(BaseModel):
    id: uuid.UUID
    severity: str
    category: str
    message: str
    detected_at: datetime
    invoice_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class InvoiceListItem(BaseModel):
    id: uuid.UUID
    invoice_number: str
    invoice_type: Optional[str] = None
    direction: str
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    currency: Optional[str] = None
    payable_amount: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    supplier_name: Optional[str] = None
    customer_name: Optional[str] = None
    source: Optional[str] = None
    anomaly_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceDetail(BaseModel):
    id: uuid.UUID
    invoice_number: str
    invoice_type: Optional[str] = None
    direction: str
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    currency: Optional[str] = None
    payable_amount: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    tax_exclusive_amount: Optional[Decimal] = None
    tax_inclusive_amount: Optional[Decimal] = None
    created_at: datetime
    supplier: Optional[PartySchema] = None
    customer: Optional[PartySchema] = None
    lines: list[InvoiceLineSchema] = []
    tax_subtotals: list[TaxSubtotalSchema] = []
    anomalies: list[AnomalySchema] = []

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    imported: int
    duplicates: int
    errors: int
    details: list[dict]


class IngestEmailRequest(BaseModel):
    eml_content: Optional[str] = None
    xml_files: Optional[list[str]] = None


class IngestProviderResponse(BaseModel):
    imported: int
    duplicates: int
    errors: int
    details: list[dict]
