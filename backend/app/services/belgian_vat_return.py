"""
Belgian VAT Return generator (Intervat XML format).
Generates a periodic VAT declaration following the official Intervat schema
used for submission to the Belgian Federal Public Service Finance.

Grid reference: https://financien.belgium.be/nl/ondernemingen/btw/aangifte/periodieke-aangifte
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


def _round2(v) -> str:
    """Round to 2 decimals and return as string."""
    if v is None:
        return "0.00"
    return str(Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


async def calculate_vat_grids(db: AsyncSession, period_start: date, period_end: date) -> dict:
    """
    Calculate Belgian VAT return grid values from invoice data.

    Belgian Intervat grids:
    Sales (output VAT):
      01 = Taxable sales at 0%
      02 = Taxable sales at 6%
      03 = Taxable sales at 12%
      44 = Services to EU businesses (intracom, 0%)
      45 = Intra-community sales
      46 = Other zero-rated sales
      47 = VAT exempt sales
      48 = Corrections on sales (positive)
      49 = Credit notes issued
      54 = VAT due on sales (01*0 + 02*0.06 + 03*0.12 + standard rate sales*0.21)

    Purchases (input VAT):
      81 = Purchases of goods/services with deductible VAT (taxable base)
      82 = Purchases without deductible VAT
      83 = Capital goods (taxable base)
      84 = Corrections on purchases
      85 = Credit notes received
      86 = Intra-community acquisitions
      87 = Other taxable acquisitions
      88 = Intra-community services (reverse charge)
      59 = Deductible VAT (input VAT on purchases)

    Summary:
      63 = VAT payable before deduction (grid 54 + 55 + 56 + 57)
      71 = Net VAT payable (63 - 59) if positive
      72 = VAT reclaimable (59 - 63) if positive
    """

    # Get invoices in the period
    period_params = {"start": period_start, "end": period_end}

    # Standard-rate sales (21%) - outbound invoices
    std_sales_r = await db.execute(text("""
        SELECT COALESCE(SUM(ts.taxable_amount), 0) as taxable, COALESCE(SUM(ts.tax_amount), 0) as vat
        FROM tax_subtotals ts
        JOIN invoices i ON ts.invoice_id = i.id
        WHERE i.direction = 'sent'
          AND i.issue_date BETWEEN :start AND :end
          AND ts.tax_percent = 21
          AND ts.tax_category = 'S'
    """), period_params)
    std_sales = std_sales_r.fetchone()

    # 6% sales
    reduced6_sales_r = await db.execute(text("""
        SELECT COALESCE(SUM(ts.taxable_amount), 0) as taxable, COALESCE(SUM(ts.tax_amount), 0) as vat
        FROM tax_subtotals ts
        JOIN invoices i ON ts.invoice_id = i.id
        WHERE i.direction = 'sent'
          AND i.issue_date BETWEEN :start AND :end
          AND ts.tax_percent = 6
    """), period_params)
    reduced6_sales = reduced6_sales_r.fetchone()

    # 12% sales
    reduced12_sales_r = await db.execute(text("""
        SELECT COALESCE(SUM(ts.taxable_amount), 0) as taxable, COALESCE(SUM(ts.tax_amount), 0) as vat
        FROM tax_subtotals ts
        JOIN invoices i ON ts.invoice_id = i.id
        WHERE i.direction = 'sent'
          AND i.issue_date BETWEEN :start AND :end
          AND ts.tax_percent = 12
    """), period_params)
    reduced12_sales = reduced12_sales_r.fetchone()

    # Zero-rated sales (Z category)
    zero_sales_r = await db.execute(text("""
        SELECT COALESCE(SUM(ts.taxable_amount), 0) as taxable
        FROM tax_subtotals ts
        JOIN invoices i ON ts.invoice_id = i.id
        WHERE i.direction = 'sent'
          AND i.issue_date BETWEEN :start AND :end
          AND ts.tax_category IN ('Z', 'G')
          AND ts.tax_percent = 0
    """), period_params)
    zero_sales = zero_sales_r.fetchone()

    # Standard rate (21%) purchases - received invoices
    std_purch_r = await db.execute(text("""
        SELECT COALESCE(SUM(ts.taxable_amount), 0) as taxable, COALESCE(SUM(ts.tax_amount), 0) as vat
        FROM tax_subtotals ts
        JOIN invoices i ON ts.invoice_id = i.id
        WHERE i.direction = 'received'
          AND i.issue_date BETWEEN :start AND :end
          AND ts.tax_percent = 21
          AND ts.tax_category = 'S'
    """), period_params)
    std_purch = std_purch_r.fetchone()

    # Reduced rate purchases (6% + 12%)
    reduced_purch_r = await db.execute(text("""
        SELECT COALESCE(SUM(ts.taxable_amount), 0) as taxable, COALESCE(SUM(ts.tax_amount), 0) as vat
        FROM tax_subtotals ts
        JOIN invoices i ON ts.invoice_id = i.id
        WHERE i.direction = 'received'
          AND i.issue_date BETWEEN :start AND :end
          AND ts.tax_percent IN (6, 12)
    """), period_params)
    reduced_purch = reduced_purch_r.fetchone()

    # Reverse charge purchases (AE category)
    rc_purch_r = await db.execute(text("""
        SELECT COALESCE(SUM(ts.taxable_amount), 0) as taxable
        FROM tax_subtotals ts
        JOIN invoices i ON ts.invoice_id = i.id
        WHERE i.direction = 'received'
          AND i.issue_date BETWEEN :start AND :end
          AND ts.tax_category = 'AE'
    """), period_params)
    rc_purch = rc_purch_r.fetchone()

    # Credit notes issued (sent, type 381)
    credit_notes_r = await db.execute(text("""
        SELECT COALESCE(ABS(SUM(ts.taxable_amount)), 0) as taxable, COALESCE(ABS(SUM(ts.tax_amount)), 0) as vat
        FROM tax_subtotals ts
        JOIN invoices i ON ts.invoice_id = i.id
        WHERE i.direction = 'sent'
          AND i.invoice_type = '381'
          AND i.issue_date BETWEEN :start AND :end
    """), period_params)
    credit_notes = credit_notes_r.fetchone()

    # Credit notes received
    credit_recv_r = await db.execute(text("""
        SELECT COALESCE(ABS(SUM(ts.taxable_amount)), 0) as taxable, COALESCE(ABS(SUM(ts.tax_amount)), 0) as vat
        FROM tax_subtotals ts
        JOIN invoices i ON ts.invoice_id = i.id
        WHERE i.direction = 'received'
          AND i.invoice_type = '381'
          AND i.issue_date BETWEEN :start AND :end
    """), period_params)
    credit_recv = credit_recv_r.fetchone()

    # Warnings
    warnings = []

    # Check for missing VAT IDs
    missing_vat_r = await db.execute(text("""
        SELECT COUNT(i.id) FROM invoices i
        JOIN parties sp ON i.supplier_id = sp.id
        WHERE i.issue_date BETWEEN :start AND :end
          AND sp.vat_id IS NULL
    """), period_params)
    missing_vat_count = missing_vat_r.scalar() or 0
    if missing_vat_count > 0:
        warnings.append(f"{missing_vat_count} invoice(s) have missing VAT IDs and may not be fully reported.")

    # Check for anomalies in period
    anomaly_r = await db.execute(text("""
        SELECT COUNT(DISTINCT a.invoice_id) FROM anomalies a
        JOIN invoices i ON a.invoice_id = i.id
        WHERE i.issue_date BETWEEN :start AND :end
          AND a.severity = 'high'
    """), period_params)
    high_anomalies = anomaly_r.scalar() or 0
    if high_anomalies > 0:
        warnings.append(f"{high_anomalies} invoice(s) with high-severity anomalies are included in this period.")

    # Calculate grid values
    g02 = Decimal(str(reduced6_sales[0]))
    g03 = Decimal(str(reduced12_sales[0]))
    g46 = Decimal(str(zero_sales[0]))
    g49 = Decimal(str(credit_notes[0]))  # credit notes issued (taxable base)

    # Standard rate sales (21%) taxable base → grid 03/other (use as standard)
    std_sales_taxable = Decimal(str(std_sales[0]))
    std_sales_vat = Decimal(str(std_sales[1]))

    # VAT due on sales (grid 54)
    g54 = (
        std_sales_vat +
        Decimal(str(reduced6_sales[1])) +
        Decimal(str(reduced12_sales[1]))
    )

    # Deductible VAT (grid 59) = VAT on purchases
    g59 = (
        Decimal(str(std_purch[1])) +
        Decimal(str(reduced_purch[1]))
    )

    # Purchases base (grid 81)
    g81 = Decimal(str(std_purch[0])) + Decimal(str(reduced_purch[0]))

    # Reverse charge (grid 88)
    g88 = Decimal(str(rc_purch[0]))

    # Credit notes received (grid 85)
    g85 = Decimal(str(credit_recv[0]))

    # Net VAT
    net_vat = g54 - g59
    g71 = max(Decimal("0"), net_vat)   # payable
    g72 = max(Decimal("0"), -net_vat)  # reclaimable

    return {
        "period_start": period_start,
        "period_end": period_end,
        "grids": {
            "02": g02,  # Taxable sales 6%
            "03": g03,  # Taxable sales 12%
            "03_std": std_sales_taxable,  # Standard rate (21%) taxable - note: grid 03 for 21% sales
            "46": g46,  # Zero-rated sales
            "49": g49,  # Credit notes issued
            "54": g54,  # VAT due on sales
            "59": g59,  # Deductible VAT
            "81": g81,  # Purchases with deductible VAT
            "85": g85,  # Credit notes received
            "88": g88,  # Intra-community services / reverse charge
            "71": g71,  # Net VAT payable
            "72": g72,  # Net VAT reclaimable
        },
        "summary": {
            "taxable_sales_21pct": float(std_sales_taxable),
            "taxable_sales_12pct": float(g03),
            "taxable_sales_6pct": float(g02),
            "taxable_sales_0pct": float(g46),
            "vat_due_on_sales": float(g54),
            "taxable_purchases": float(g81),
            "deductible_vat": float(g59),
            "net_vat_payable": float(g71),
            "net_vat_reclaimable": float(g72),
        },
        "warnings": warnings,
    }


def generate_intervat_xml(
    grids: dict,
    declarant_vat: str,
    declarant_name: str,
    declarant_street: str,
    declarant_city: str,
    declarant_postal: str,
    declarant_email: str,
    period_start,
    period_end,
    declaration_reference: str = None,
) -> str:
    """
    Generate Intervat XML for Belgian VAT return.
    Format follows the official Belgian FPS Finance Intervat schema.
    """
    import uuid
    from datetime import datetime

    if declaration_reference is None:
        declaration_reference = f"REF-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Determine period (monthly/quarterly)
    # Period format: YYYYMM for monthly, YYYYQN for quarterly
    period_str = period_start.strftime("%Y%m")

    g = grids["grids"]

    def grid_xml(number: str, value) -> str:
        v = Decimal(str(value))
        if v == 0:
            return ""
        return f'      <ns2:Amount GridNumber="{number}">{_round2(v)}</ns2:Amount>\n'

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<ns2:VATConsignment
  xmlns:ns2="http://www.minfin.fgov.be/VATConsignment"
  VATDeclarationNbr="1"
  xsi:noNamespaceSchemaLocation="NewTVA-in_v0_8.xsd"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <ns2:VATDeclaration SequenceNumber="1" DeclarantReference="{declaration_reference}">
    <ns2:Declarant>
      <ns2:VATNumber issuedBy="BE">{declarant_vat.replace("BE", "").replace("be", "")}</ns2:VATNumber>
      <ns2:Name>{declarant_name}</ns2:Name>
      <ns2:Street>{declarant_street}</ns2:Street>
      <ns2:PostCode>{declarant_postal}</ns2:PostCode>
      <ns2:City>{declarant_city}</ns2:City>
      <ns2:CountryCode>BE</ns2:CountryCode>
      <ns2:EmailAddress>{declarant_email}</ns2:EmailAddress>
    </ns2:Declarant>
    <ns2:Period>{period_str}</ns2:Period>
    <ns2:Data>
{grid_xml("02", g.get("02", 0))}
{grid_xml("03", g.get("03", 0))}
{grid_xml("46", g.get("46", 0))}
{grid_xml("49", g.get("49", 0))}
{grid_xml("54", g.get("54", 0))}
{grid_xml("59", g.get("59", 0))}
{grid_xml("81", g.get("81", 0))}
{grid_xml("85", g.get("85", 0))}
{grid_xml("88", g.get("88", 0))}
{grid_xml("71", g.get("71", 0))}
{grid_xml("72", g.get("72", 0))}
    </ns2:Data>
  </ns2:VATDeclaration>
</ns2:VATConsignment>'''

    return xml
