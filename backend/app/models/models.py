import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    String, Text, DateTime, Date, Numeric, ForeignKey, func, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# NOTE: For existing databases, new columns will NOT be added automatically by
# create_all. Run Alembic migrations or ALTER TABLE statements manually to add
# the new columns to existing tables.


class RawInvoiceFile(Base):
    __tablename__ = "raw_invoice_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    invoices: Mapped[list["Invoice"]] = relationship("Invoice", back_populates="raw_file")


class Party(Base):
    __tablename__ = "parties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    vat_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    endpoint_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    iban: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Address
    street_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    additional_street_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    city_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    postal_zone: Mapped[str | None] = mapped_column(Text, nullable=True)
    country_subentity: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_line: Mapped[str | None] = mapped_column(Text, nullable=True)  # extra address line

    # Legal entity
    registration_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_id: Mapped[str | None] = mapped_column(Text, nullable=True)  # legal entity company ID / CBE number
    company_legal_form: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Contact
    contact_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_telephone: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Peppol
    endpoint_scheme: Mapped[str | None] = mapped_column(Text, nullable=True)  # e.g. "0208"

    supplier_invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice", foreign_keys="Invoice.supplier_id", back_populates="supplier"
    )
    customer_invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice", foreign_keys="Invoice.customer_id", back_populates="customer"
    )
    payee_invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice", foreign_keys="Invoice.payee_party_id", back_populates="payee_party"
    )
    tax_rep_invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice", foreign_keys="Invoice.tax_representative_party_id", back_populates="tax_representative_party"
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    raw_file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("raw_invoice_files.id"), nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(256), nullable=False)
    invoice_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="received")
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("parties.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("parties.id"), nullable=False)
    payable_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    tax_exclusive_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    tax_inclusive_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # UBL header metadata
    customization_id: Mapped[str | None] = mapped_column(Text, nullable=True)   # cbc:CustomizationID
    profile_id: Mapped[str | None] = mapped_column(Text, nullable=True)         # cbc:ProfileID
    note: Mapped[str | None] = mapped_column(Text, nullable=True)               # cbc:Note
    tax_point_date: Mapped[date | None] = mapped_column(Date, nullable=True)    # cbc:TaxPointDate
    tax_currency_code: Mapped[str | None] = mapped_column(Text, nullable=True)  # cbc:TaxCurrencyCode
    accounting_cost: Mapped[str | None] = mapped_column(Text, nullable=True)    # cbc:AccountingCost (buyer booking ref)
    buyer_reference: Mapped[str | None] = mapped_column(Text, nullable=True)    # cbc:BuyerReference

    # Invoice period
    invoice_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    invoice_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    invoice_period_description_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    # References
    order_reference_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    sales_order_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    billing_reference_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    billing_reference_issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    despatch_document_reference_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_document_reference_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    originator_document_reference_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_document_reference_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_reference_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional parties
    payee_party_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("parties.id"), nullable=True)
    tax_representative_party_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("parties.id"), nullable=True)

    # Delivery
    delivery_actual_delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delivery_location_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_street_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_city_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_postal_zone: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_country_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_party_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Payment means
    payment_means_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_means_payment_id: Mapped[str | None] = mapped_column(Text, nullable=True)  # structured comm / payment ref
    payment_means_iban: Mapped[str | None] = mapped_column(Text, nullable=True)  # keep existing iban moved here
    payment_means_swift: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_terms_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Document-level allowances/charges summary
    allowance_total_amount: Mapped[Decimal | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    charge_total_amount: Mapped[Decimal | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    prepaid_amount: Mapped[Decimal | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    payable_rounding_amount: Mapped[Decimal | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    line_extension_amount: Mapped[Decimal | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)  # sum of lines

    # Peppol source tracking
    peppol_document_id: Mapped[str | None] = mapped_column(Text, nullable=True)  # ID from e-invoice.be API
    peppol_state: Mapped[str | None] = mapped_column(Text, nullable=True)  # DRAFT, TRANSIT, FAILED, SENT, RECEIVED
    peppol_sender_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    peppol_receiver_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    raw_file: Mapped["RawInvoiceFile"] = relationship("RawInvoiceFile", back_populates="invoices")
    supplier: Mapped["Party"] = relationship("Party", foreign_keys=[supplier_id], back_populates="supplier_invoices")
    customer: Mapped["Party"] = relationship("Party", foreign_keys=[customer_id], back_populates="customer_invoices")
    payee_party: Mapped["Party | None"] = relationship("Party", foreign_keys=[payee_party_id], back_populates="payee_invoices")
    tax_representative_party: Mapped["Party | None"] = relationship("Party", foreign_keys=[tax_representative_party_id], back_populates="tax_rep_invoices")
    lines: Mapped[list["InvoiceLine"]] = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    tax_subtotals: Mapped[list["TaxSubtotal"]] = relationship("TaxSubtotal", back_populates="invoice", cascade="all, delete-orphan")
    anomalies: Mapped[list["Anomaly"]] = relationship("Anomaly", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    line_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    line_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    tax_category: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tax_percent: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    # Extended UBL fields
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    accounting_cost: Mapped[str | None] = mapped_column(Text, nullable=True)  # buyer accounting reference for line
    item_name: Mapped[str | None] = mapped_column(Text, nullable=True)  # cac:Item/cbc:Name (BT-153)
    buyers_item_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    sellers_item_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    standard_item_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    item_origin_country: Mapped[str | None] = mapped_column(Text, nullable=True)
    commodity_classification_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    invoice_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    order_line_reference_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(precision=18, scale=4), nullable=True)
    tax_exemption_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    tax_exemption_reason_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="lines")


class TaxSubtotal(Base):
    __tablename__ = "tax_subtotals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    tax_category: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tax_percent: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    taxable_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    tax_exemption_reason_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    tax_exemption_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="tax_subtotals")


class ReportRun(Base):
    __tablename__ = "report_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    report_definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generated_sql: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Who ran it
    actor: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Validation results
    validation_errors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)    # list of validation errors from Step 1+2
    dataset_completeness: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # Step 3: {total, matched, excluded, reasons}
    reconciliation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)        # Step 4: {report_total, independent_total, match}
    data_quality_score: Mapped[dict | None] = mapped_column(JSONB, nullable=True)   # Step 6: {score, checks}


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    invoice: Mapped["Invoice | None"] = relationship("Invoice", back_populates="anomalies")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(Text, nullable=False)       # e.g. "report.generate", "invoice.import", "invoice.sync"
    entity_type: Mapped[str | None] = mapped_column(Text, nullable=True)   # e.g. "report_run", "invoice"
    entity_id: Mapped[str | None] = mapped_column(Text, nullable=True)     # UUID of affected entity
    actor: Mapped[str | None] = mapped_column(Text, nullable=True)         # user identifier from X-User-Id header or "system"
    ip_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)      # arbitrary metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
