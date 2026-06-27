"""
Report engine: compiles a ReportDefinition into safe parameterised SQL
and executes it against the async SQLAlchemy session.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.report import ALLOWED_FIELDS, Filter, Metric, OrderBy, ReportDefinition


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
            params[lo_name] = f.value[0]
            params[hi_name] = f.value[1]
            clauses.append(f"{col} BETWEEN :{lo_name} AND :{hi_name}")

        elif f.operator == "in":
            if not isinstance(f.value, (list, tuple)):
                raise ValueError(f"'in' operator requires a list for field '{f.field}'")
            placeholders = []
            for i, val in enumerate(f.value):
                pn = f"{param_name}_i{i}"
                params[pn] = val
                placeholders.append(f":{pn}")
            clauses.append(f"{col} IN ({', '.join(placeholders)})")

        else:
            tmpl = _OP_MAP.get(f.operator)
            if not tmpl:
                raise ValueError(f"Unknown operator '{f.operator}'")
            params[param_name] = f.value
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
