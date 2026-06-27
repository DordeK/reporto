"""
Report generation and retrieval endpoints.
"""
from __future__ import annotations

import time
import uuid
from datetime import date as _date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.models import ReportRun
<<<<<<< Updated upstream
from app.schemas.report import GenerateReportRequest, ReportDefinition
from app.services.ai_service import dispatch_prompt, explain_report, generate_report_definition
from app.services.report_engine import execute_report
=======
from app.services.ai_service import explain_report, generate_report_definition, dispatch_prompt
from app.services.report_engine import execute_report, GenerateReportRequest, ReportDefinition
>>>>>>> Stashed changes
from app.services.report_validator import (
    validate_report_definition,
    validate_sql,
    get_dataset_completeness,
    reconcile_report,
    compute_data_quality_score,
    verify_ubl_accounting_identity,
    check_currency_mixing,
)
from app.services import audit_service

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /reports/generate
# ---------------------------------------------------------------------------

@router.post("/generate")
async def generate_report(
    body: GenerateReportRequest,
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """
    Natural language → report definition → SQL → results → explanation.
    Runs the full validation pipeline (Steps 1–4, 6) and enriches the response.
    """
    actor = request.headers.get("X-User-Id", "anonymous") if request else "anonymous"
    ip_address = request.client.host if (request and request.client) else None

    # 1. Dispatch: LLM picks the right tool and extracts params
    dispatch = await dispatch_prompt(body.prompt)
    tool = dispatch["tool"]
    args = dispatch["args"]

    # ── Slovenian DDV (KPR + DDV-O XML) ──────────────────────────────────────
    if tool == "generate_slovenian_ddv":
        from app.services.slovenian_vat_return import (
            fetch_purchase_ledger, compute_ddvo_boxes,
            generate_kpr_xml, generate_ddvo_xml,
        )
        from datetime import date as _date
        year = _date.today().year
        ps = _date.fromisoformat(args.get("period_start", f"{year}-01-01"))
        pe = _date.fromisoformat(args.get("period_end",   f"{year}-03-31"))
        entries = await fetch_purchase_ledger(db, ps, pe)
        boxes   = await compute_ddvo_boxes(db, ps, pe)
        return {
            "reportType":       "slovenian_ddv",
            "reportDefinition": {"name": "Slovenian DDV Return (KPR + DDV-O)"},
            "rows":             [],
            "explanation": (
                f"Generated Slovenian eDavki XML for {ps} – {pe}. "
                f"{len(entries)} purchase entries. "
                "Download KPR (Knjiga Prejetih Računov) and DDV-O (Periodična DDV napoved) "
                "and upload to beta.edavki.durs.si."
            ),
            "xmlData": {
                "kpr_xml":     generate_kpr_xml(entries, args.get("tax_number", "12345678"), ps, pe),
                "ddvo_xml":    generate_ddvo_xml(
                                   boxes, args.get("tax_number", "12345678"),
                                   args.get("taxpayer_name", "Demo Company d.o.o."), ps, pe),
                "boxes":       boxes,
                "entry_count": len(entries),
                "kpr_schema":  "http://edavki.durs.si/Documents/Schemas/KPR_3.xsd",
                "ddvo_schema": "http://edavki.durs.si/Documents/Schemas/DDVO_4.xsd",
            },
            "warnings": [] if entries else ["No received invoices found for this period."],
        }

    # ── Belgian Intervat VAT return ───────────────────────────────────────────
    if tool == "generate_belgian_vat":
        from app.services.belgian_vat_return import calculate_vat_grids, generate_intervat_xml
        from datetime import date as _date
        year = _date.today().year
        ps = _date.fromisoformat(args.get("period_start", f"{year}-01-01"))
        pe = _date.fromisoformat(args.get("period_end",   f"{year}-03-31"))
        grids = await calculate_vat_grids(db, ps, pe)
        xml_content = generate_intervat_xml(
            grids=grids,
            declarant_vat=args.get("declarant_vat",    "BE0000000000"),
            declarant_name=args.get("declarant_name",  "Demo Company NV"),
            declarant_street=args.get("declarant_street", ""),
            declarant_city=args.get("declarant_city",   ""),
            declarant_postal=args.get("declarant_postal", ""),
            declarant_email=args.get("declarant_email",  ""),
            period_start=ps, period_end=pe,
        )
        return {
            "reportType":       "belgian_vat",
            "reportDefinition": {"name": "Belgian Intervat VAT Return"},
            "rows":             [],
            "explanation": (
                f"Generated Belgian Intervat XML for {ps} – {pe}. "
                "Download and upload to intervat.minfinbe."
            ),
            "xmlData": {"vat_xml": xml_content, "grids": grids},
            "warnings": grids.get("warnings", []),
        }

    # ── SQL analytics report (existing pipeline) ─────────────────────────────
    raw_definition = args

    # Handle non-report inputs gracefully
    if raw_definition.get("not_a_report"):
        raise HTTPException(
            status_code=400,
            detail={"type": "not_a_report", "message": raw_definition.get("message", "Please ask a report-related question.")},
        )

    # 2. Validate the definition with Pydantic
    try:
        report_def_obj = ReportDefinition(**raw_definition)
    except (ValidationError, Exception) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"AI produced an invalid report definition: {exc}",
        )

    # Step 1 validation: field/aggregation/operator checks
    validation_errors = validate_report_definition(raw_definition)

    # 3 & 4. Compile to SQL (reuse report_engine compile path)
    try:
        from app.services.report_engine import compile_to_sql
        sql, sql_params = compile_to_sql(report_def_obj)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"SQL compilation failed: {exc}",
        )

    # Step 2 validation: EXPLAIN the SQL
    sql_errors = await validate_sql(db, sql, sql_params)
    if sql_errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "SQL validation failed", "errors": sql_errors},
        )

    # Execute the SQL
    start = time.time()
    try:
        sql, rows = await execute_report(db, report_def_obj)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Report execution failed: {exc}",
        )
    execution_time_ms = int((time.time() - start) * 1000)

    # Step 3: Dataset completeness
    completeness = await get_dataset_completeness(db, raw_definition)

    # Step 4: Reconciliation
    reconciliation = await reconcile_report(db, raw_definition, rows)

    # Step 7: UBL accounting identity (BT-115 = BT-109 + BT-110 − BT-113)
    ubl_identity = await verify_ubl_accounting_identity(db, raw_definition)

    # Step 8: Currency mixing warning
    currency_check = await check_currency_mixing(db, raw_definition)

    # Step 6: Data quality score
    quality_score = await compute_data_quality_score(db)

    # 5. Generate explanation
    explanation = await explain_report(body.prompt, raw_definition, rows, len(rows))

    # 6. Persist the report run
    run = ReportRun(
        id=uuid.uuid4(),
        user_prompt=body.prompt,
        report_definition=raw_definition,
        generated_sql=sql,
        result={"rows": rows, "row_count": len(rows)},
        explanation=explanation,
        actor=actor,
        ip_address=ip_address,
        execution_time_ms=execution_time_ms,
        row_count=len(rows),
        validation_errors=validation_errors if validation_errors else None,
        dataset_completeness=completeness,
        reconciliation={**reconciliation, "ubl_identity": ubl_identity, "currency_check": currency_check},
        data_quality_score=quality_score,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Audit log
    await audit_service.log_action(
        db, action="report.generate",
        entity_type="report_run", entity_id=str(run.id),
        actor=actor, ip_address=ip_address,
        details={"prompt": body.prompt, "report_name": raw_definition.get("reportName"), "row_count": len(rows)},
    )
    await db.commit()

    return {
        "reportDefinition": raw_definition,
        "sql": sql,
        "rows": rows,
        "explanation": explanation,
        "reportRunId": str(run.id),
        "validation": {
            "errors": validation_errors + sql_errors,
            "warnings": [currency_check["warning"]] if currency_check.get("warning") else [],
            "passed": len(validation_errors) == 0 and len(sql_errors) == 0,
        },
        "datasetCompleteness": completeness,
        "reconciliation": {**reconciliation, "ubl_identity": ubl_identity, "currency_check": currency_check},
        "dataQualityScore": quality_score,
    }


# ---------------------------------------------------------------------------
# GET /reports
# ---------------------------------------------------------------------------

@router.get("")
async def list_reports(db: AsyncSession = Depends(get_db)):
    """Return a summary list of all report runs."""
    result = await db.execute(
        select(ReportRun).order_by(ReportRun.created_at.desc()).limit(100)
    )
    runs = result.scalars().all()

    return [
        {
            "id": str(r.id),
            "user_prompt": r.user_prompt,
            "report_name": r.report_definition.get("reportName", "Unnamed") if r.report_definition else "Unnamed",
            "row_count": (r.result or {}).get("row_count", 0),
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


# ---------------------------------------------------------------------------
# GET /reports/{run_id}
# ---------------------------------------------------------------------------

@router.get("/{run_id}/drilldown")
async def report_drilldown(run_id: str, group_key: str = None, db: AsyncSession = Depends(get_db)):
    """
    Drill down into individual invoices for a given report run.
    Optionally filter by a group_key (JSON string of {field: value}).
    """
    import json

    # Load report run
    result = await db.execute(select(ReportRun).where(ReportRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Report run not found")

    report_def = run.report_definition

    # Build drill-down query
    params = {}
    where_parts = ["1=1"]

    _DATE_COLS = {"i.issue_date", "i.due_date", "i.tax_point_date",
                  "i.invoice_period_start", "i.invoice_period_end",
                  "i.delivery_actual_delivery_date"}

    def _coerce(col: str, v):
        if col in _DATE_COLS and isinstance(v, str):
            try:
                return _date.fromisoformat(v)
            except ValueError:
                pass
        return v

    # Apply report filters
    for idx, flt in enumerate(report_def.get("filters", [])):
        field = flt.get("field", "")
        op = flt.get("operator", "eq")
        value = flt.get("value")
        col_map = {
            "invoice.issue_date": "i.issue_date",
            "invoice.due_date": "i.due_date",
            "invoice.currency": "i.currency",
            "invoice.direction": "i.direction",
            "supplier.name": "sp.name",
            "supplier.vat_id": "sp.vat_id",
            "tax_subtotals.tax_percent": "ts.tax_percent",
            "tax_subtotals.tax_category": "ts.tax_category",
        }
        col = col_map.get(field)
        if not col:
            continue
        pk = f"df_{idx}"
        if op == "between":
            where_parts.append(f"{col} BETWEEN :{pk}_a AND :{pk}_b")
            params[f"{pk}_a"] = _coerce(col, value[0])
            params[f"{pk}_b"] = _coerce(col, value[1])
        elif op == "eq":
            where_parts.append(f"{col} = :{pk}")
            params[pk] = _coerce(col, value)
        elif op == "gte":
            where_parts.append(f"{col} >= :{pk}")
            params[pk] = _coerce(col, value)
        elif op == "lte":
            where_parts.append(f"{col} <= :{pk}")
            params[pk] = _coerce(col, value)

    # Apply group key filter
    if group_key:
        try:
            gk = json.loads(group_key)
            for gidx, (gfield, gvalue) in enumerate(gk.items()):
                gcol_map = {
                    "supplier.name": "sp.name",
                    "supplier.vat_id": "sp.vat_id",
                    "tax_subtotals.tax_percent": "ts.tax_percent",
                    "tax_subtotals.tax_category": "ts.tax_category",
                    "invoice.currency": "i.currency",
                }
                gcol = gcol_map.get(gfield)
                if gcol and gvalue is not None:
                    gk_param = f"gk_{gidx}"
                    where_parts.append(f"{gcol} = :{gk_param}")
                    params[gk_param] = gvalue
        except Exception:
            pass

    entity = report_def.get("entity", "invoices")
    if entity == "tax_subtotals":
        join_clause = "tax_subtotals ts JOIN invoices i ON ts.invoice_id = i.id"
    elif entity == "invoice_lines":
        join_clause = "invoice_lines il JOIN invoices i ON il.invoice_id = i.id"
    else:
        join_clause = "invoices i"

    drilldown_sql = f"""
        SELECT DISTINCT i.id, i.invoice_number, i.issue_date, i.payable_amount, i.tax_amount, i.currency,
               sp.name as supplier_name, sp.vat_id as supplier_vat_id,
               cu.name as customer_name
        FROM {join_clause}
        LEFT JOIN parties sp ON i.supplier_id = sp.id
        LEFT JOIN parties cu ON i.customer_id = cu.id
        WHERE {" AND ".join(where_parts)}
        ORDER BY i.issue_date DESC
        LIMIT 200
    """

    rows_result = await db.execute(text(drilldown_sql), params)
    rows = rows_result.mappings().all()

    return {
        "invoices": [
            {
                "id": str(r["id"]),
                "invoice_number": r["invoice_number"],
                "issue_date": r["issue_date"].isoformat() if r["issue_date"] else None,
                "payable_amount": float(r["payable_amount"]) if r["payable_amount"] else None,
                "tax_amount": float(r["tax_amount"]) if r["tax_amount"] else None,
                "currency": r["currency"],
                "supplier_name": r["supplier_name"],
                "supplier_vat_id": r["supplier_vat_id"],
                "customer_name": r["customer_name"],
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get("/{run_id}")
async def get_report(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Return the full details of a single report run."""
    result = await db.execute(select(ReportRun).where(ReportRun.id == run_id))
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Report run not found")

    return {
        "id": str(run.id),
        "user_prompt": run.user_prompt,
        "report_definition": run.report_definition,
        "generated_sql": run.generated_sql,
        "result": run.result,
        "explanation": run.explanation,
        "created_at": run.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# POST /reports/belgian-vat-return
# ---------------------------------------------------------------------------

@router.post("/belgian-vat-return")
async def generate_belgian_vat_return(
    body: dict,  # expects: {period_start, period_end, declarant_vat, declarant_name, declarant_street, declarant_city, declarant_postal, declarant_email}
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    from app.services.belgian_vat_return import calculate_vat_grids, generate_intervat_xml
    from datetime import date

    period_start = date.fromisoformat(body.get("period_start", "2026-01-01"))
    period_end = date.fromisoformat(body.get("period_end", "2026-03-31"))

    grids = await calculate_vat_grids(db, period_start, period_end)

    xml_content = generate_intervat_xml(
        grids=grids,
        declarant_vat=body.get("declarant_vat", "BE0000000000"),
        declarant_name=body.get("declarant_name", "Your Company"),
        declarant_street=body.get("declarant_street", ""),
        declarant_city=body.get("declarant_city", ""),
        declarant_postal=body.get("declarant_postal", ""),
        declarant_email=body.get("declarant_email", ""),
        period_start=period_start,
        period_end=period_end,
    )

    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "grids": grids,
        "xml": xml_content,
        "format": "Intervat XML (Belgian FPS Finance)",
        "warnings": grids.get("warnings", []),
    }


# ---------------------------------------------------------------------------
# POST /reports/slovenian-vat-return
# ---------------------------------------------------------------------------

@router.post("/slovenian-vat-return")
async def generate_slovenian_vat_return(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate official Slovenian DDV documents for eDavki submission:
      - KPR (Knjiga Prejetih Računov / Purchase Ledger)
      - DDV-O (Periodična DDV napoved / Periodic VAT Return)

    Portal: https://beta.edavki.durs.si
    Authority: FURS — Finančna uprava Republike Slovenije
    """
    from app.services.slovenian_vat_return import (
        fetch_purchase_ledger,
        compute_ddvo_boxes,
        generate_kpr_xml,
        generate_ddvo_xml,
    )
    from datetime import date as _date

    period_start = _date.fromisoformat(body.get("period_start", "2026-01-01"))
    period_end   = _date.fromisoformat(body.get("period_end",   "2026-03-31"))
    tax_number   = body.get("tax_number",    "12345678")
    taxpayer_name = body.get("taxpayer_name", "Your Company d.o.o.")

    entries = await fetch_purchase_ledger(db, period_start, period_end)
    boxes   = await compute_ddvo_boxes(db, period_start, period_end)

    kpr_xml  = generate_kpr_xml(entries, tax_number, period_start, period_end)
    ddvo_xml = generate_ddvo_xml(boxes, tax_number, taxpayer_name, period_start, period_end)

    warnings = []
    if not entries:
        warnings.append("No received invoices found for this period — KPR contains no entries.")

    return {
        "period_start":    period_start.isoformat(),
        "period_end":      period_end.isoformat(),
        "entry_count":     len(entries),
        "boxes":           boxes,
        "kpr_xml":         kpr_xml,
        "ddvo_xml":        ddvo_xml,
        "format":          "eDavki XML (FURS — Finančna uprava RS)",
        "kpr_schema":      "http://edavki.durs.si/Documents/Schemas/KPR_3.xsd",
        "ddvo_schema":     "http://edavki.durs.si/Documents/Schemas/DDVO_4.xsd",
        "warnings":        warnings,
    }
