"""
Report engine: compiles a ReportDefinition into safe parameterised SQL
and executes it against the async SQLAlchemy session.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


ALLOWED_FIELDS = {
    # ── Invoice header (UBL 2.1 / Peppol BIS 3.0 Business Terms) ──────────────
    "invoice.invoice_number":              ("invoices", "invoice_number"),          # BT-1
    "invoice.invoice_type":                ("invoices", "invoice_type"),            # BT-3
    "invoice.issue_date":                  ("invoices", "issue_date"),              # BT-2
    "invoice.due_date":                    ("invoices", "due_date"),                # BT-9
    "invoice.tax_point_date":              ("invoices", "tax_point_date"),          # BT-7
    "invoice.currency":                    ("invoices", "currency"),                # BT-5
    "invoice.tax_currency_code":           ("invoices", "tax_currency_code"),       # BT-6
    "invoice.direction":                   ("invoices", "direction"),               # received | sent
    "invoice.note":                        ("invoices", "note"),                    # BT-22
    "invoice.buyer_reference":             ("invoices", "buyer_reference"),         # BT-10
    "invoice.accounting_cost":             ("invoices", "accounting_cost"),         # BT-19
    "invoice.customization_id":            ("invoices", "customization_id"),        # BT-24
    "invoice.profile_id":                  ("invoices", "profile_id"),              # BT-23
    "invoice.invoice_period_start":        ("invoices", "invoice_period_start"),    # BT-73
    "invoice.invoice_period_end":          ("invoices", "invoice_period_end"),      # BT-74
    "invoice.order_reference_id":          ("invoices", "order_reference_id"),      # BT-13
    "invoice.sales_order_id":              ("invoices", "sales_order_id"),          # BT-14
    "invoice.contract_document_reference_id": ("invoices", "contract_document_reference_id"),  # BT-12
    "invoice.billing_reference_id":        ("invoices", "billing_reference_id"),    # BT-25
    "invoice.project_reference_id":        ("invoices", "project_reference_id"),    # BT-11
    "invoice.despatch_document_reference_id": ("invoices", "despatch_document_reference_id"),  # BT-16
    "invoice.receipt_document_reference_id": ("invoices", "receipt_document_reference_id"),    # BT-15
    "invoice.payment_means_code":          ("invoices", "payment_means_code"),      # BT-81
    "invoice.payment_terms_note":          ("invoices", "payment_terms_note"),      # BT-20
    "invoice.line_extension_amount":       ("invoices", "line_extension_amount"),   # BT-106
    "invoice.allowance_total_amount":      ("invoices", "allowance_total_amount"),  # BT-107
    "invoice.charge_total_amount":         ("invoices", "charge_total_amount"),     # BT-108
    "invoice.tax_exclusive_amount":        ("invoices", "tax_exclusive_amount"),    # BT-109
    "invoice.tax_amount":                  ("invoices", "tax_amount"),              # BT-110
    "invoice.tax_inclusive_amount":        ("invoices", "tax_inclusive_amount"),    # BT-112
    "invoice.prepaid_amount":              ("invoices", "prepaid_amount"),          # BT-113
    "invoice.payable_amount":              ("invoices", "payable_amount"),          # BT-115
    "invoice.delivery_actual_delivery_date": ("invoices", "delivery_actual_delivery_date"),  # BT-72
    "invoice.delivery_country_code":       ("invoices", "delivery_country_code"),   # BT-80
    "invoice.delivery_city_name":          ("invoices", "delivery_city_name"),
    "invoice.peppol_state":                ("invoices", "peppol_state"),
    # ── Supplier (BG-4) ───────────────────────────────────────────────────────
    "supplier.name":              ("supplier", "name"),
    "supplier.vat_id":            ("supplier", "vat_id"),
    "supplier.country_code":      ("supplier", "country_code"),
    "supplier.city_name":         ("supplier", "city_name"),
    "supplier.postal_zone":       ("supplier", "postal_zone"),
    "supplier.registration_name": ("supplier", "registration_name"),
    "supplier.company_id":        ("supplier", "company_id"),
    "supplier.endpoint_id":       ("supplier", "endpoint_id"),
    "supplier.endpoint_scheme":   ("supplier", "endpoint_scheme"),
    # ── Customer (BG-7) ───────────────────────────────────────────────────────
    "customer.name":              ("customer", "name"),
    "customer.vat_id":            ("customer", "vat_id"),
    "customer.country_code":      ("customer", "country_code"),
    "customer.city_name":         ("customer", "city_name"),
    "customer.registration_name": ("customer", "registration_name"),
    "customer.company_id":        ("customer", "company_id"),
    # ── Tax subtotals (BG-23) ─────────────────────────────────────────────────
    "tax_subtotals.tax_category":              ("tax_subtotals", "tax_category"),
    "tax_subtotals.tax_percent":               ("tax_subtotals", "tax_percent"),
    "tax_subtotals.taxable_amount":            ("tax_subtotals", "taxable_amount"),
    "tax_subtotals.tax_amount":                ("tax_subtotals", "tax_amount"),
    "tax_subtotals.tax_exemption_reason_code": ("tax_subtotals", "tax_exemption_reason_code"),
    # ── Invoice lines (BG-25) ─────────────────────────────────────────────────
    "invoice_lines.description":              ("invoice_lines", "description"),
    "invoice_lines.item_name":                ("invoice_lines", "item_name"),
    "invoice_lines.quantity":                 ("invoice_lines", "quantity"),
    "invoice_lines.unit_price":               ("invoice_lines", "unit_price"),
    "invoice_lines.line_amount":              ("invoice_lines", "line_amount"),
    "invoice_lines.tax_category":             ("invoice_lines", "tax_category"),
    "invoice_lines.tax_percent":              ("invoice_lines", "tax_percent"),
    "invoice_lines.accounting_cost":          ("invoice_lines", "accounting_cost"),
    "invoice_lines.sellers_item_id":          ("invoice_lines", "sellers_item_id"),
    "invoice_lines.buyers_item_id":           ("invoice_lines", "buyers_item_id"),
    "invoice_lines.standard_item_id":         ("invoice_lines", "standard_item_id"),
    "invoice_lines.commodity_classification_code": ("invoice_lines", "commodity_classification_code"),
    "invoice_lines.item_origin_country":      ("invoice_lines", "item_origin_country"),
    "invoice_lines.tax_exemption_reason_code": ("invoice_lines", "tax_exemption_reason_code"),
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

# Fields whose values must be coerced to datetime.date before passing to asyncpg
_DATE_FIELDS = {
    "invoice.issue_date",
    "invoice.due_date",
    "invoice.tax_point_date",
    "invoice.invoice_period_start",
    "invoice.invoice_period_end",
    "invoice.delivery_actual_delivery_date",
    "invoice.billing_reference_issue_date",
}


def _coerce_value(field: str, value: Any) -> Any:
    """Convert string dates to datetime.date for date-typed fields."""
    if field in _DATE_FIELDS and isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return value
    return value


# ---------------------------------------------------------------------------
# Field → SQL column resolution
# ---------------------------------------------------------------------------

def _resolve_column(field: str) -> str:
    """Map a dot-notation field name to its fully qualified SQL column."""
    table, column = ALLOWED_FIELDS[field]
    if table == "supplier":
        return f"supplier.{column}"
    if table == "customer":
        return f"customer.{column}"
    return f"{table}.{column}"


# ---------------------------------------------------------------------------
# JOIN analysis
# ---------------------------------------------------------------------------

def _required_joins(entity: str, all_fields: list[str]) -> dict[str, bool]:
    """Determine which JOINs are needed given the entity and referenced fields."""
    joins: dict[str, bool] = {
        "supplier": False,
        "customer": False,
        "invoices_from_subtotals": False,
        "invoices_from_lines": False,
    }

    for field in all_fields:
        if field.startswith("supplier."):
            joins["supplier"] = True
        if field.startswith("customer."):
            joins["customer"] = True
        if field.startswith("invoice.") and entity in ("tax_subtotals", "invoice_lines"):
            if entity == "tax_subtotals":
                joins["invoices_from_subtotals"] = True
            else:
                joins["invoices_from_lines"] = True

    # If entity is invoices and we need supplier/customer
    # those joins are always appended when their fields appear.

    return joins


# ---------------------------------------------------------------------------
# Operator → SQL snippet
# ---------------------------------------------------------------------------

_OP_MAP = {
    "eq": "= :{param}",
    "neq": "!= :{param}",
    "gt": "> :{param}",
    "gte": ">= :{param}",
    "lt": "< :{param}",
    "lte": "<= :{param}",
    "like": "LIKE :{param}",
}


def _build_where(filters: list[Filter], params: dict[str, Any]) -> str:
    """Build the WHERE clause and populate the params dict."""
    clauses: list[str] = []
    for idx, f in enumerate(filters):
        col = _resolve_column(f.field)
        param_name = f"p{idx}"

        if f.operator == "between":
            if not isinstance(f.value, (list, tuple)) or len(f.value) != 2:
                raise ValueError(f"'between' operator requires a list of 2 values for field '{f.field}'")
            lo_name = f"{param_name}_lo"
            hi_name = f"{param_name}_hi"
            params[lo_name] = _coerce_value(f.field, f.value[0])
            params[hi_name] = _coerce_value(f.field, f.value[1])
            clauses.append(f"{col} BETWEEN :{lo_name} AND :{hi_name}")

        elif f.operator == "in":
            if not isinstance(f.value, (list, tuple)):
                raise ValueError(f"'in' operator requires a list for field '{f.field}'")
            placeholders = []
            for i, val in enumerate(f.value):
                pn = f"{param_name}_i{i}"
                params[pn] = _coerce_value(f.field, val)
                placeholders.append(f":{pn}")
            clauses.append(f"{col} IN ({', '.join(placeholders)})")

        else:
            tmpl = _OP_MAP.get(f.operator)
            if not tmpl:
                raise ValueError(f"Unknown operator '{f.operator}'")
            params[param_name] = _coerce_value(f.field, f.value)
            clauses.append(f"{col} {tmpl.format(param=param_name)}")

    return " AND ".join(clauses) if clauses else ""


# ---------------------------------------------------------------------------
# Main compiler
# ---------------------------------------------------------------------------

def compile_to_sql(report_def: ReportDefinition) -> tuple[str, dict[str, Any]]:
    """
    Compile a validated ReportDefinition into a parameterised SQL string
    and a params dict.

    Returns:
        (sql_string, params_dict)
    """
    params: dict[str, Any] = {}

    # Collect all referenced fields for JOIN analysis
    all_referenced: list[str] = []
    for f in report_def.filters:
        all_referenced.append(f.field)
    for g in report_def.groupBy:
        all_referenced.append(g)
    for m in report_def.metrics:
        if m.field != "*":
            all_referenced.append(m.field)
    for o in report_def.orderBy:
        if o.field in ALLOWED_FIELDS:
            all_referenced.append(o.field)

    joins = _required_joins(report_def.entity, all_referenced)

    # ── FROM clause ──────────────────────────────────────────────────────────
    from_clause = report_def.entity

    join_clauses: list[str] = []

    if report_def.entity == "tax_subtotals":
        if joins["invoices_from_subtotals"] or joins["supplier"] or joins["customer"]:
            join_clauses.append(
                "JOIN invoices ON tax_subtotals.invoice_id = invoices.id"
            )
    elif report_def.entity == "invoice_lines":
        if joins["invoices_from_lines"] or joins["supplier"] or joins["customer"]:
            join_clauses.append(
                "JOIN invoices ON invoice_lines.invoice_id = invoices.id"
            )

    if joins["supplier"]:
        join_clauses.append(
            "JOIN parties AS supplier ON invoices.supplier_id = supplier.id"
        )
    if joins["customer"]:
        join_clauses.append(
            "JOIN parties AS customer ON invoices.customer_id = customer.id"
        )

    # ── SELECT clause ────────────────────────────────────────────────────────
    select_parts: list[str] = []

    # GROUP BY columns first
    group_cols: list[str] = []
    for field in report_def.groupBy:
        col = _resolve_column(field)
        select_parts.append(col)
        group_cols.append(col)

    # Metrics
    for metric in report_def.metrics:
        if metric.field == "*":
            expr = f"{metric.aggregation.upper()}(*)"
        else:
            col = _resolve_column(metric.field)
            expr = f"{metric.aggregation.upper()}({col})"
        select_parts.append(f"{expr} AS {metric.alias}")

    if not select_parts:
        select_parts = ["*"]

    # ── WHERE clause ─────────────────────────────────────────────────────────
    where_sql = _build_where(report_def.filters, params)

    # ── ORDER BY clause ───────────────────────────────────────────────────────
    order_parts: list[str] = []
    for o in report_def.orderBy:
        if o.field in ALLOWED_FIELDS:
            col = _resolve_column(o.field)
        else:
            # assume it's an alias
            col = o.field
        order_parts.append(f"{col} {o.direction.upper()}")

    # ── Assemble ──────────────────────────────────────────────────────────────
    sql_lines = [f"SELECT {', '.join(select_parts)}"]
    sql_lines.append(f"FROM {from_clause}")
    for jc in join_clauses:
        sql_lines.append(jc)
    if where_sql:
        sql_lines.append(f"WHERE {where_sql}")
    if group_cols:
        sql_lines.append(f"GROUP BY {', '.join(group_cols)}")
    if order_parts:
        sql_lines.append(f"ORDER BY {', '.join(order_parts)}")
    sql_lines.append(f"LIMIT :limit_val")
    params["limit_val"] = report_def.limit

    sql = "\n".join(sql_lines)
    return sql, params


async def execute_report(
    db: AsyncSession,
    report_def: ReportDefinition,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Compile and execute the report.

    Returns:
        (sql_string, rows_as_list_of_dicts)
    """
    sql, params = compile_to_sql(report_def)
    result = await db.execute(text(sql), params)
    columns = list(result.keys())
    rows = [dict(zip(columns, row)) for row in result.fetchall()]

    # Serialise non-JSON-serialisable types
    serialised: list[dict[str, Any]] = []
    for row in rows:
        clean: dict[str, Any] = {}
        for k, v in row.items():
            if hasattr(v, "isoformat"):
                clean[k] = v.isoformat()
            elif hasattr(v, "__float__"):
                # Decimal
                clean[k] = float(v)
            else:
                clean[k] = v
        serialised.append(clean)

    return sql, serialised
