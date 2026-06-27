import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, field_validator


ALLOWED_FIELDS = {
    "invoice.issue_date": ("invoices", "issue_date"),
    "invoice.due_date": ("invoices", "due_date"),
    "invoice.currency": ("invoices", "currency"),
    "invoice.direction": ("invoices", "direction"),
    "invoice.payable_amount": ("invoices", "payable_amount"),
    "invoice.invoice_number": ("invoices", "invoice_number"),
    "supplier.name": ("supplier", "name"),
    "supplier.vat_id": ("supplier", "vat_id"),
    "supplier.country_code": ("supplier", "country_code"),
    "customer.name": ("customer", "name"),
    "customer.vat_id": ("customer", "vat_id"),
    "tax_subtotals.tax_category": ("tax_subtotals", "tax_category"),
    "tax_subtotals.tax_percent": ("tax_subtotals", "tax_percent"),
    "tax_subtotals.taxable_amount": ("tax_subtotals", "taxable_amount"),
    "tax_subtotals.tax_amount": ("tax_subtotals", "tax_amount"),
    "invoice_lines.description": ("invoice_lines", "description"),
    "invoice_lines.line_amount": ("invoice_lines", "line_amount"),
    "invoice_lines.tax_category": ("invoice_lines", "tax_category"),
    "invoice_lines.tax_percent": ("invoice_lines", "tax_percent"),
}

ALLOWED_OPERATORS = {"eq", "neq", "gt", "gte", "lt", "lte", "between", "in", "like"}
ALLOWED_AGGREGATIONS = {"sum", "count", "avg", "min", "max"}
ALLOWED_DIRECTIONS = {"asc", "desc"}
ALLOWED_ENTITIES = {"invoices", "tax_subtotals", "invoice_lines"}


class Filter(BaseModel):
    field: str
    operator: str
    value: Any

    @field_validator("field")
    @classmethod
    def validate_field(cls, v: str) -> str:
        if v not in ALLOWED_FIELDS:
            raise ValueError(f"Field '{v}' is not in ALLOWED_FIELDS")
        return v

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        if v not in ALLOWED_OPERATORS:
            raise ValueError(f"Operator '{v}' is not allowed")
        return v


class Metric(BaseModel):
    field: str
    aggregation: str
    alias: str

    @field_validator("field")
    @classmethod
    def validate_field(cls, v: str) -> str:
        if v != "*" and v not in ALLOWED_FIELDS:
            raise ValueError(f"Field '{v}' is not in ALLOWED_FIELDS")
        return v

    @field_validator("aggregation")
    @classmethod
    def validate_aggregation(cls, v: str) -> str:
        if v not in ALLOWED_AGGREGATIONS:
            raise ValueError(f"Aggregation '{v}' is not allowed")
        return v


class OrderBy(BaseModel):
    field: str
    direction: str = "asc"

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        if v.lower() not in ALLOWED_DIRECTIONS:
            raise ValueError(f"Direction '{v}' must be 'asc' or 'desc'")
        return v.lower()


class ReportDefinition(BaseModel):
    reportName: str
    entity: str
    filters: list[Filter] = []
    groupBy: list[str] = []
    metrics: list[Metric]
    orderBy: list[OrderBy] = []
    limit: int = 1000

    @field_validator("entity")
    @classmethod
    def validate_entity(cls, v: str) -> str:
        if v not in ALLOWED_ENTITIES:
            raise ValueError(f"Entity '{v}' is not allowed. Must be one of {ALLOWED_ENTITIES}")
        return v

    @field_validator("groupBy")
    @classmethod
    def validate_group_by(cls, v: list[str]) -> list[str]:
        for field in v:
            if field not in ALLOWED_FIELDS:
                raise ValueError(f"groupBy field '{field}' is not in ALLOWED_FIELDS")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 10000:
            raise ValueError("limit must be between 1 and 10000")
        return v


class GenerateReportRequest(BaseModel):
    prompt: str


class ReportRunSummary(BaseModel):
    id: uuid.UUID
    user_prompt: str
    report_name: str
    row_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportRunDetail(BaseModel):
    id: uuid.UUID
    user_prompt: str
    report_definition: dict
    generated_sql: Optional[str] = None
    result: Optional[dict] = None
    explanation: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GenerateReportResponse(BaseModel):
    reportDefinition: dict
    sql: str
    rows: list[dict]
    explanation: str
    reportRunId: uuid.UUID
