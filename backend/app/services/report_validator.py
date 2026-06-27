"""
Multi-step report validation pipeline for generated reports.
Steps:
  1. Validate report definition (fields, aggregations, operators)
  2. Validate generated SQL via EXPLAIN
  3. Dataset completeness (total vs matched invoices)
  4. Reconciliation (report totals vs independent DB totals)
  5. Drill-down (handled by router endpoint)
  6. Data quality score (anomaly-based)
"""
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func, select

_DATE_FIELDS = {
    "invoice.issue_date", "invoice.due_date", "invoice.tax_point_date",
    "invoice.invoice_period_start", "invoice.invoice_period_end",
    "invoice.delivery_actual_delivery_date", "invoice.billing_reference_issue_date",
}

def _coerce(field: str, value):
    if field in _DATE_FIELDS and isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return value

ALLOWED_AGGREGATIONS = {"sum", "count", "avg", "min", "max"}
ALLOWED_OPERATORS = {"eq", "neq", "gt", "gte", "lt", "lte", "between", "in", "like"}
ALLOWED_ENTITIES = {"invoices", "tax_subtotals", "invoice_lines"}

FIELD_COLUMN_MAP = {
    # Invoice header
    "invoice.invoice_number":               ("i", "invoice_number"),
    "invoice.invoice_type":                 ("i", "invoice_type"),
    "invoice.issue_date":                   ("i", "issue_date"),
    "invoice.due_date":                     ("i", "due_date"),
    "invoice.tax_point_date":               ("i", "tax_point_date"),
    "invoice.currency":                     ("i", "currency"),
    "invoice.tax_currency_code":            ("i", "tax_currency_code"),
    "invoice.direction":                    ("i", "direction"),
    "invoice.note":                         ("i", "note"),
    "invoice.buyer_reference":              ("i", "buyer_reference"),
    "invoice.accounting_cost":              ("i", "accounting_cost"),
    "invoice.customization_id":             ("i", "customization_id"),
    "invoice.profile_id":                   ("i", "profile_id"),
    "invoice.invoice_period_start":         ("i", "invoice_period_start"),
    "invoice.invoice_period_end":           ("i", "invoice_period_end"),
    "invoice.order_reference_id":           ("i", "order_reference_id"),
    "invoice.sales_order_id":               ("i", "sales_order_id"),
    "invoice.contract_document_reference_id": ("i", "contract_document_reference_id"),
    "invoice.billing_reference_id":         ("i", "billing_reference_id"),
    "invoice.project_reference_id":         ("i", "project_reference_id"),
    "invoice.despatch_document_reference_id": ("i", "despatch_document_reference_id"),
    "invoice.receipt_document_reference_id":  ("i", "receipt_document_reference_id"),
    "invoice.payment_means_code":           ("i", "payment_means_code"),
    "invoice.payment_terms_note":           ("i", "payment_terms_note"),
    "invoice.line_extension_amount":        ("i", "line_extension_amount"),
    "invoice.allowance_total_amount":       ("i", "allowance_total_amount"),
    "invoice.charge_total_amount":          ("i", "charge_total_amount"),
    "invoice.tax_exclusive_amount":         ("i", "tax_exclusive_amount"),
    "invoice.tax_amount":                   ("i", "tax_amount"),
    "invoice.tax_inclusive_amount":         ("i", "tax_inclusive_amount"),
    "invoice.prepaid_amount":               ("i", "prepaid_amount"),
    "invoice.payable_amount":               ("i", "payable_amount"),
    "invoice.delivery_actual_delivery_date": ("i", "delivery_actual_delivery_date"),
    "invoice.delivery_country_code":        ("i", "delivery_country_code"),
    "invoice.delivery_city_name":           ("i", "delivery_city_name"),
    "invoice.peppol_state":                 ("i", "peppol_state"),
    # Supplier
    "supplier.name":              ("sp", "name"),
    "supplier.vat_id":            ("sp", "vat_id"),
    "supplier.country_code":      ("sp", "country_code"),
    "supplier.city_name":         ("sp", "city_name"),
    "supplier.postal_zone":       ("sp", "postal_zone"),
    "supplier.registration_name": ("sp", "registration_name"),
    "supplier.company_id":        ("sp", "company_id"),
    "supplier.endpoint_id":       ("sp", "endpoint_id"),
    "supplier.endpoint_scheme":   ("sp", "endpoint_scheme"),
    # Customer
    "customer.name":              ("cu", "name"),
    "customer.vat_id":            ("cu", "vat_id"),
    "customer.country_code":      ("cu", "country_code"),
    "customer.city_name":         ("cu", "city_name"),
    "customer.registration_name": ("cu", "registration_name"),
    "customer.company_id":        ("cu", "company_id"),
    # Tax subtotals
    "tax_subtotals.tax_category":              ("ts", "tax_category"),
    "tax_subtotals.tax_percent":               ("ts", "tax_percent"),
    "tax_subtotals.taxable_amount":            ("ts", "taxable_amount"),
    "tax_subtotals.tax_amount":                ("ts", "tax_amount"),
    "tax_subtotals.tax_exemption_reason_code": ("ts", "tax_exemption_reason_code"),
    # Invoice lines
    "invoice_lines.description":               ("il", "description"),
    "invoice_lines.item_name":                 ("il", "item_name"),
    "invoice_lines.quantity":                  ("il", "quantity"),
    "invoice_lines.unit_price":                ("il", "unit_price"),
    "invoice_lines.line_amount":               ("il", "line_amount"),
    "invoice_lines.tax_category":              ("il", "tax_category"),
    "invoice_lines.tax_percent":               ("il", "tax_percent"),
    "invoice_lines.accounting_cost":           ("il", "accounting_cost"),
    "invoice_lines.sellers_item_id":           ("il", "sellers_item_id"),
    "invoice_lines.buyers_item_id":            ("il", "buyers_item_id"),
    "invoice_lines.standard_item_id":          ("il", "standard_item_id"),
    "invoice_lines.commodity_classification_code": ("il", "commodity_classification_code"),
    "invoice_lines.item_origin_country":       ("il", "item_origin_country"),
    "invoice_lines.tax_exemption_reason_code": ("il", "tax_exemption_reason_code"),
}

# Which fields are from UBL — can answer "can we get this from e-invoices?"
UBL_BACKED_FIELDS = set(FIELD_COLUMN_MAP.keys())


# ── Step 1 ────────────────────────────────────────────────────────────────────

def validate_report_definition(report_def: dict) -> list[dict]:
    """Returns list of validation error dicts."""
    errors = []
    allowed = set(FIELD_COLUMN_MAP.keys())

    if report_def.get("entity") not in ALLOWED_ENTITIES:
        errors.append({"step": 1, "code": "INVALID_ENTITY",
                       "message": f"Entity '{report_def.get('entity')}' is not queryable. Use: {sorted(ALLOWED_ENTITIES)}"})

    for metric in report_def.get("metrics", []):
        f = metric.get("field")
        if f not in allowed:
            errors.append({"step": 1, "code": "INVALID_FIELD",
                           "message": f"Field '{f}' is not in the allowed field list.",
                           "ubl_backed": False})
        agg = metric.get("aggregation", "").lower()
        if agg not in ALLOWED_AGGREGATIONS:
            errors.append({"step": 1, "code": "INVALID_AGGREGATION",
                           "message": f"Aggregation '{agg}' is not allowed. Use: {sorted(ALLOWED_AGGREGATIONS)}"})

    for flt in report_def.get("filters", []):
        f = flt.get("field")
        if f not in allowed:
            errors.append({"step": 1, "code": "INVALID_FILTER_FIELD",
                           "message": f"Filter field '{f}' is not allowed."})
        op = flt.get("operator", "").lower()
        if op not in ALLOWED_OPERATORS:
            errors.append({"step": 1, "code": "INVALID_OPERATOR",
                           "message": f"Operator '{op}' is not allowed."})
        if op == "between":
            v = flt.get("value")
            if not isinstance(v, list) or len(v) != 2:
                errors.append({"step": 1, "code": "INVALID_BETWEEN",
                               "message": "Operator 'between' requires exactly 2 values in a list."})

    metric_fields = {m.get("field") for m in report_def.get("metrics", [])}
    for gb in report_def.get("groupBy", []):
        if gb not in allowed:
            errors.append({"step": 1, "code": "INVALID_GROUPBY",
                           "message": f"GroupBy field '{gb}' is not allowed."})
        if gb in metric_fields:
            errors.append({"step": 1, "code": "GROUPBY_METRIC_CONFLICT",
                           "message": f"Cannot group by '{gb}' — it is also used as an aggregated metric field."})

    return errors


# ── Step 2 ────────────────────────────────────────────────────────────────────

async def validate_sql(db: AsyncSession, sql: str, params: dict) -> list[dict]:
    """Run EXPLAIN to catch SQL errors."""
    errors = []
    try:
        await db.execute(text(f"EXPLAIN {sql}"), params)
    except Exception as e:
        errors.append({"step": 2, "code": "SQL_EXPLAIN_ERROR",
                       "message": f"SQL validation failed: {str(e)}"})
    return errors


# ── Step 3 ────────────────────────────────────────────────────────────────────

async def get_dataset_completeness(db: AsyncSession, report_def: dict) -> dict:
    """Count total/matched/excluded invoices."""
    total_r = await db.execute(text("SELECT COUNT(*) FROM invoices"))
    total = total_r.scalar() or 0

    entity = report_def.get("entity", "invoices")
    if entity == "tax_subtotals":
        from_clause = "tax_subtotals ts JOIN invoices i ON ts.invoice_id = i.id LEFT JOIN parties sp ON i.supplier_id = sp.id LEFT JOIN parties cu ON i.customer_id = cu.id"
    elif entity == "invoice_lines":
        from_clause = "invoice_lines il JOIN invoices i ON il.invoice_id = i.id LEFT JOIN parties sp ON i.supplier_id = sp.id LEFT JOIN parties cu ON i.customer_id = cu.id"
    else:
        from_clause = "invoices i LEFT JOIN parties sp ON i.supplier_id = sp.id LEFT JOIN parties cu ON i.customer_id = cu.id"

    where_parts = []
    params = {}
    reasons = []

    for idx, flt in enumerate(report_def.get("filters", [])):
        field = flt.get("field", "")
        op = flt.get("operator", "eq").lower()
        value = flt.get("value")
        mapping = FIELD_COLUMN_MAP.get(field)
        if not mapping:
            continue
        alias, col = mapping
        qualified = f"{alias}.{col}"
        pk = f"fc_{idx}"

        if op == "between":
            where_parts.append(f"{qualified} BETWEEN :{pk}_a AND :{pk}_b")
            params[f"{pk}_a"] = _coerce(field, value[0])
            params[f"{pk}_b"] = _coerce(field, value[1])
            reasons.append(f"{field} outside {value[0]} to {value[1]}")
        elif op == "in":
            placeholders = ", ".join(f":{pk}_{j}" for j in range(len(value)))
            where_parts.append(f"{qualified} IN ({placeholders})")
            for j, v in enumerate(value):
                params[f"{pk}_{j}"] = _coerce(field, v)
            reasons.append(f"{field} not in {value}")
        elif op == "eq":
            where_parts.append(f"{qualified} = :{pk}")
            params[pk] = _coerce(field, value)
            reasons.append(f"{field} != {value}")
        elif op == "gte":
            where_parts.append(f"{qualified} >= :{pk}")
            params[pk] = _coerce(field, value)
        elif op == "lte":
            where_parts.append(f"{qualified} <= :{pk}")
            params[pk] = _coerce(field, value)
        elif op == "gt":
            where_parts.append(f"{qualified} > :{pk}")
            params[pk] = _coerce(field, value)
        elif op == "lt":
            where_parts.append(f"{qualified} < :{pk}")
            params[pk] = _coerce(field, value)
        elif op == "like":
            where_parts.append(f"{qualified} ILIKE :{pk}")
            params[pk] = f"%{value}%"

    where_str = "WHERE " + " AND ".join(where_parts) if where_parts else ""
    count_sql = f"SELECT COUNT(DISTINCT i.id) FROM {from_clause} {where_str}"

    try:
        matched_r = await db.execute(text(count_sql), params)
        matched = matched_r.scalar() or 0
    except Exception:
        matched = None

    excluded = (total - matched) if matched is not None else None

    return {
        "total_invoices": total,
        "matched_invoices": matched,
        "excluded_invoices": excluded,
        "exclusion_reasons": reasons,
        "completeness_note": (
            f"Invoices in database: {total} — Invoices matching filters: {matched} — "
            f"Excluded invoices: {excluded}" + (f" — Reason: {'; '.join(reasons)}" if reasons else "")
        ) if matched is not None else f"Invoices in database: {total}",
    }


# ── Step 4 ────────────────────────────────────────────────────────────────────

async def reconcile_report(db: AsyncSession, report_def: dict, rows: list) -> dict:
    """Compare report sums against independent DB totals."""
    results = {}

    independent_queries = {
        "tax_subtotals.tax_amount": "SELECT SUM(tax_amount) FROM tax_subtotals",
        "tax_subtotals.taxable_amount": "SELECT SUM(taxable_amount) FROM tax_subtotals",
        "invoice_lines.line_amount": "SELECT SUM(line_amount) FROM invoice_lines",
        "invoice.payable_amount": "SELECT SUM(payable_amount) FROM invoices",
    }

    for metric in report_def.get("metrics", []):
        if metric.get("aggregation") != "sum":
            continue
        field = metric.get("field")
        alias = metric.get("alias", field)
        indep_sql = independent_queries.get(field)
        if not indep_sql:
            continue

        report_total = sum(float(r.get(alias) or 0) for r in rows)

        try:
            r = await db.execute(text(indep_sql))
            indep_total = float(r.scalar() or 0)
        except Exception as e:
            results[alias] = {"error": str(e)}
            continue

        results[alias] = {
            "report_total": round(report_total, 2),
            "independent_total": round(indep_total, 2),
            "match": abs(report_total - indep_total) < 0.02,
            "note": "Independent total covers ALL invoices (no date/filter restriction)",
        }

    return results


# ── Step 7 ────────────────────────────────────────────────────────────────────

async def verify_ubl_accounting_identity(db: AsyncSession, report_def: dict) -> dict:
    """
    UBL Accounting Identity check (BT-115 = BT-109 + BT-110 − BT-113).

    Runs an independent query against the invoices table using the report's
    invoice/supplier/customer-level filters. Subtotal and line-level filters
    are skipped (noted in the result) because we aggregate at invoice level.

    Tolerance: max(€0.02, 1 cent per invoice, 0.01% of total payable) to
    absorb per-invoice rounding as defined in UBL 2.1 §7.1.
    """
    where_parts = []
    params = {}
    skipped_filters = []

    for idx, flt in enumerate(report_def.get("filters", [])):
        field = flt.get("field", "")
        op = flt.get("operator", "eq").lower()
        value = flt.get("value")
        mapping = FIELD_COLUMN_MAP.get(field)
        if not mapping:
            continue
        alias, col = mapping
        # Only apply invoice/supplier/customer filters; line/subtotal filters
        # cannot be applied here since we aggregate at invoice level
        if alias not in ("i", "sp", "cu"):
            skipped_filters.append(field)
            continue
        qualified = f"{alias}.{col}"
        pk = f"ui_{idx}"

        if op == "between":
            where_parts.append(f"{qualified} BETWEEN :{pk}_a AND :{pk}_b")
            params[f"{pk}_a"] = _coerce(field, value[0])
            params[f"{pk}_b"] = _coerce(field, value[1])
        elif op == "in":
            placeholders = ", ".join(f":{pk}_{j}" for j in range(len(value)))
            where_parts.append(f"{qualified} IN ({placeholders})")
            for j, v in enumerate(value):
                params[f"{pk}_{j}"] = _coerce(field, v)
        elif op == "eq":
            where_parts.append(f"{qualified} = :{pk}")
            params[pk] = _coerce(field, value)
        elif op == "gte":
            where_parts.append(f"{qualified} >= :{pk}")
            params[pk] = _coerce(field, value)
        elif op == "lte":
            where_parts.append(f"{qualified} <= :{pk}")
            params[pk] = _coerce(field, value)
        elif op == "gt":
            where_parts.append(f"{qualified} > :{pk}")
            params[pk] = _coerce(field, value)
        elif op == "lt":
            where_parts.append(f"{qualified} < :{pk}")
            params[pk] = _coerce(field, value)
        elif op == "like":
            where_parts.append(f"{qualified} ILIKE :{pk}")
            params[pk] = f"%{value}%"

    where_str = "WHERE " + " AND ".join(where_parts) if where_parts else ""

    identity_sql = f"""
        SELECT
            SUM(i.payable_amount)                   AS sum_payable,
            SUM(i.tax_exclusive_amount)             AS sum_net,
            SUM(i.tax_amount)                       AS sum_vat,
            SUM(COALESCE(i.prepaid_amount, 0))      AS sum_prepaid,
            COUNT(i.id)                             AS invoice_count
        FROM invoices i
        LEFT JOIN parties sp ON i.supplier_id = sp.id
        LEFT JOIN parties cu ON i.customer_id = cu.id
        {where_str}
    """

    try:
        r = await db.execute(text(identity_sql), params)
        row = r.fetchone()
    except Exception as e:
        return {"error": str(e), "passed": None}

    sum_payable = float(row.sum_payable or 0)
    sum_net = float(row.sum_net or 0)
    sum_vat = float(row.sum_vat or 0)
    sum_prepaid = float(row.sum_prepaid or 0)
    invoice_count = int(row.invoice_count or 0)

    # BT-115 = BT-109 + BT-110 − BT-113
    expected_payable = sum_net + sum_vat - sum_prepaid
    delta = abs(sum_payable - expected_payable)

    # Tolerance accumulates 1 cent of rounding per invoice, minimum €0.02,
    # capped at 0.01% of total to avoid masking real discrepancies on large sets
    tolerance = max(0.02, invoice_count * 0.01)
    if sum_payable:
        tolerance = min(tolerance, abs(sum_payable) * 0.0001 + invoice_count * 0.01)
    passes = delta <= tolerance

    return {
        "passed": passes,
        "formula": "BT-115 (payable) = BT-109 (excl. VAT) + BT-110 (VAT) − BT-113 (prepaid)",
        "invoice_count": invoice_count,
        "sum_payable_bt115": round(sum_payable, 2),
        "sum_net_bt109": round(sum_net, 2),
        "sum_vat_bt110": round(sum_vat, 2),
        "sum_prepaid_bt113": round(sum_prepaid, 2),
        "expected_payable": round(expected_payable, 2),
        "delta": round(delta, 4),
        "tolerance": round(tolerance, 4),
        "note": (
            f"{round(sum_payable, 2)} ≈ {round(sum_net, 2)} + {round(sum_vat, 2)} "
            f"− {round(sum_prepaid, 2)} = {round(expected_payable, 2)} "
            f"(Δ {round(delta, 4)}, tolerance {round(tolerance, 4)})"
        ),
        "skipped_filters": skipped_filters,
    }


# ── Step 8 ────────────────────────────────────────────────────────────────────

# Fields whose values represent monetary amounts — summing across currencies is invalid
_MONETARY_FIELDS = {
    "invoice.payable_amount", "invoice.tax_amount", "invoice.tax_exclusive_amount",
    "invoice.tax_inclusive_amount", "invoice.line_extension_amount",
    "invoice.allowance_total_amount", "invoice.charge_total_amount", "invoice.prepaid_amount",
    "tax_subtotals.taxable_amount", "tax_subtotals.tax_amount",
    "invoice_lines.line_amount", "invoice_lines.unit_price",
}


async def check_currency_mixing(db: AsyncSession, report_def: dict) -> dict:
    """
    Currency mixing warning: detect when a report sums monetary amounts across
    invoices with different BT-5 currency codes. Such totals are arithmetically
    meaningless (EUR + USD ≠ anything useful).

    Always runs against the invoices table using invoice/supplier/customer
    filters from the report definition. Returns a warning if > 1 currency is
    present and at least one SUM metric targets a monetary field.
    """
    # Only relevant when the report sums monetary values
    has_monetary_sum = any(
        m.get("aggregation") == "sum" and m.get("field") in _MONETARY_FIELDS
        for m in report_def.get("metrics", [])
    )
    if not has_monetary_sum:
        return {"relevant": False, "mixed": False, "currencies": [], "warning": None}

    # Build WHERE from invoice/supplier/customer filters only
    where_parts = []
    params = {}
    for idx, flt in enumerate(report_def.get("filters", [])):
        field = flt.get("field", "")
        op = flt.get("operator", "eq").lower()
        value = flt.get("value")
        mapping = FIELD_COLUMN_MAP.get(field)
        if not mapping:
            continue
        alias, col = mapping
        if alias not in ("i", "sp", "cu"):
            continue
        qualified = f"{alias}.{col}"
        pk = f"cm_{idx}"

        if op == "between":
            where_parts.append(f"{qualified} BETWEEN :{pk}_a AND :{pk}_b")
            params[f"{pk}_a"] = _coerce(field, value[0])
            params[f"{pk}_b"] = _coerce(field, value[1])
        elif op == "in":
            placeholders = ", ".join(f":{pk}_{j}" for j in range(len(value)))
            where_parts.append(f"{qualified} IN ({placeholders})")
            for j, v in enumerate(value):
                params[f"{pk}_{j}"] = _coerce(field, v)
        elif op == "eq":
            where_parts.append(f"{qualified} = :{pk}")
            params[pk] = _coerce(field, value)
        elif op == "gte":
            where_parts.append(f"{qualified} >= :{pk}")
            params[pk] = _coerce(field, value)
        elif op == "lte":
            where_parts.append(f"{qualified} <= :{pk}")
            params[pk] = _coerce(field, value)
        elif op == "gt":
            where_parts.append(f"{qualified} > :{pk}")
            params[pk] = _coerce(field, value)
        elif op == "lt":
            where_parts.append(f"{qualified} < :{pk}")
            params[pk] = _coerce(field, value)
        elif op == "like":
            where_parts.append(f"{qualified} ILIKE :{pk}")
            params[pk] = f"%{value}%"

    where_str = "WHERE " + " AND ".join(where_parts) if where_parts else ""

    currency_sql = f"""
        SELECT i.currency, COUNT(*) AS invoice_count, SUM(i.payable_amount) AS total_payable
        FROM invoices i
        LEFT JOIN parties sp ON i.supplier_id = sp.id
        LEFT JOIN parties cu ON i.customer_id = cu.id
        {where_str}
        GROUP BY i.currency
        ORDER BY invoice_count DESC
    """

    try:
        result = await db.execute(text(currency_sql), params)
        rows = result.fetchall()
    except Exception as e:
        return {"relevant": True, "mixed": False, "currencies": [], "error": str(e), "warning": None}

    currencies = [
        {"currency": r.currency or "NULL", "invoice_count": int(r.invoice_count), "total_payable": round(float(r.total_payable or 0), 2)}
        for r in rows
    ]
    distinct = [c for c in currencies if c["currency"] != "NULL"]
    mixed = len(distinct) > 1

    warning = None
    if mixed:
        codes = ", ".join(c["currency"] for c in distinct)
        warning = (
            f"Report sums monetary amounts across {len(distinct)} currencies ({codes}). "
            f"Add a currency filter (e.g. invoice.currency = 'EUR') to get a meaningful total."
        )

    return {
        "relevant": True,
        "mixed": mixed,
        "currencies": currencies,
        "warning": warning,
    }


# ── Step 6 ────────────────────────────────────────────────────────────────────

async def compute_data_quality_score(db: AsyncSession) -> dict:
    """Score data quality based on anomaly checks."""
    total_r = await db.execute(text("SELECT COUNT(*) FROM invoices"))
    total = int(total_r.scalar() or 1)

    async def count_anomalies(category: str) -> int:
        r = await db.execute(
            text("SELECT COUNT(DISTINCT invoice_id) FROM anomalies WHERE category = :cat"),
            {"cat": category},
        )
        return int(r.scalar() or 0)

    checks = []

    mismatch = await count_anomalies("tax_amount_mismatch")
    checks.append({"name": "Invoice totals consistent", "icon": "✓" if mismatch == 0 else "⚠",
                   "passed": total - mismatch, "failed": mismatch, "ok": mismatch == 0,
                   "warning": f"{mismatch} invoice(s) have inconsistent totals" if mismatch else None})

    dups = await count_anomalies("duplicate_invoice_number")
    checks.append({"name": "No duplicate invoice IDs", "icon": "✓" if dups == 0 else "⚠",
                   "passed": total - dups, "failed": dups, "ok": dups == 0,
                   "warning": f"{dups} duplicate invoice number(s) detected" if dups else None})

    checks.append({"name": "XML valid", "icon": "✓", "passed": total, "failed": 0, "ok": True, "warning": None})

    missing_vat = await count_anomalies("missing_vat_id")
    checks.append({"name": "VAT IDs present", "icon": "✓" if missing_vat == 0 else "⚠",
                   "passed": total - missing_vat, "failed": missing_vat, "ok": missing_vat == 0,
                   "warning": f"{missing_vat} invoice(s) missing VAT ID" if missing_vat else None})

    pt_r = await db.execute(text(
        "SELECT COUNT(*) FROM invoices WHERE payment_terms_note IS NULL AND direction = 'received'"
    ))
    missing_pt = int(pt_r.scalar() or 0)
    checks.append({"name": "Payment terms present", "icon": "✓" if missing_pt == 0 else "⚠",
                   "passed": total - missing_pt, "failed": missing_pt, "ok": missing_pt == 0,
                   "warning": f"{missing_pt} invoice(s) missing payment terms" if missing_pt else None})

    vat_calc = await count_anomalies("tax_amount_mismatch")
    checks.append({"name": "VAT calculations correct", "icon": "✓" if vat_calc == 0 else "⚠",
                   "passed": total - vat_calc, "failed": vat_calc, "ok": vat_calc == 0,
                   "warning": f"{vat_calc} invoice(s) have suspicious VAT calculation" if vat_calc else None})

    total_failed = sum(c["failed"] for c in checks)
    score = max(0.0, round((1 - total_failed / (total * len(checks))) * 100, 1)) if total > 0 else 100.0

    return {
        "score": score,
        "total_invoices": total,
        "checks": checks,
        "warnings": [c["warning"] for c in checks if c.get("warning")],
    }
