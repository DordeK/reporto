"use client";

import { InvoiceDetail as IDetail } from "@/lib/api";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import Link from "next/link";

const formatEur = (v: number, currency = "EUR") =>
  new Intl.NumberFormat("en-EU", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(v);

const formatDate = (d?: string) => {
  if (!d) return "—";
  try {
    return new Date(d).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return d;
  }
};

const SEVERITY_STYLE: Record<string, { bg: string; color: string; border: string }> = {
  high: { bg: "rgba(239,68,68,0.1)", color: "#f87171", border: "#ef4444" },
  medium: { bg: "rgba(245,158,11,0.1)", color: "#fbbf24", border: "#f59e0b" },
  low: { bg: "rgba(59,130,246,0.1)", color: "#60a5fa", border: "#3b82f6" },
};

const SOURCE_STYLE: Record<string, { bg: string; color: string }> = {
  upload: { bg: "rgba(59,130,246,0.15)", color: "#60a5fa" },
  email: { bg: "rgba(34,197,94,0.15)", color: "#4ade80" },
  provider: { bg: "rgba(168,85,247,0.15)", color: "#c084fc" },
};

interface InvoiceDetailProps {
  invoice: IDetail;
}

export default function InvoiceDetailComponent({ invoice }: InvoiceDetailProps) {
  const src = SOURCE_STYLE[invoice.source] || SOURCE_STYLE.upload;

  return (
    <div className="space-y-5">
      {/* Back + Header */}
      <div>
        <Link
          href="/invoices"
          className="inline-flex items-center gap-1 text-sm mb-4 transition-colors"
          style={{ color: "#64748b", textDecoration: "none" }}
        >
          <ArrowLeft size={14} />
          Back to Invoices
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: "#f1f5f9", letterSpacing: "-0.02em" }}>
              {invoice.invoice_number}
            </h1>
            <div className="flex items-center gap-2 mt-2">
              {invoice.invoice_type && (
                <span
                  className="text-xs px-2 py-1 rounded"
                  style={{ background: "#334155", color: "#94a3b8" }}
                >
                  {invoice.invoice_type}
                </span>
              )}
              {invoice.direction && (
                <span
                  className="text-xs px-2 py-1 rounded font-medium"
                  style={{
                    background: invoice.direction === "received"
                      ? "rgba(34,197,94,0.15)"
                      : "rgba(168,85,247,0.15)",
                    color: invoice.direction === "received" ? "#4ade80" : "#c084fc",
                  }}
                >
                  {invoice.direction === "received" ? "Received" : "Sent"}
                </span>
              )}
              <span
                className="text-xs px-2 py-1 rounded font-medium"
                style={{ background: src.bg, color: src.color }}
              >
                {invoice.source.charAt(0).toUpperCase() + invoice.source.slice(1)}
              </span>
              {invoice.anomaly_count > 0 && (
                <span
                  className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded font-medium"
                  style={{ background: "rgba(239,68,68,0.15)", color: "#f87171" }}
                >
                  <AlertTriangle size={11} />
                  {invoice.anomaly_count} anomal{invoice.anomaly_count === 1 ? "y" : "ies"}
                </span>
              )}
            </div>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold" style={{ color: "#f1f5f9" }}>
              {formatEur(invoice.payable_amount, invoice.currency)}
            </div>
            <div className="text-sm mt-1" style={{ color: "#64748b" }}>
              incl. VAT {formatEur(invoice.tax_amount, invoice.currency)}
            </div>
          </div>
        </div>
      </div>

      {/* Supplier / Customer */}
      <div className="grid grid-cols-2 gap-4">
        {[
          {
            label: "Supplier",
            name: invoice.supplier_name,
            vatId: invoice.supplier_vat_id,
            country: invoice.supplier_country,
            iban: invoice.supplier_iban,
            address: invoice.supplier_address,
          },
          {
            label: "Customer",
            name: invoice.customer_name,
            vatId: invoice.customer_vat_id,
            country: invoice.customer_country,
            iban: invoice.customer_iban,
            address: invoice.customer_address,
          },
        ].map((party) => (
          <div
            key={party.label}
            className="rounded-xl p-4"
            style={{ background: "#1e293b", border: "1px solid #334155" }}
          >
            <p className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "#64748b" }}>
              {party.label}
            </p>
            <p className="font-semibold" style={{ color: "#f1f5f9" }}>
              {party.name}
            </p>
            {party.address && (
              <p className="text-sm mt-1" style={{ color: "#94a3b8" }}>
                {party.address}
              </p>
            )}
            <div className="mt-3 space-y-1">
              {party.vatId && (
                <div className="flex items-center gap-2">
                  <span className="text-xs" style={{ color: "#64748b", width: 48 }}>VAT ID</span>
                  <span className="text-xs font-mono" style={{ color: "#94a3b8" }}>{party.vatId}</span>
                </div>
              )}
              {party.country && (
                <div className="flex items-center gap-2">
                  <span className="text-xs" style={{ color: "#64748b", width: 48 }}>Country</span>
                  <span className="text-xs" style={{ color: "#94a3b8" }}>{party.country}</span>
                </div>
              )}
              {party.iban && (
                <div className="flex items-center gap-2">
                  <span className="text-xs" style={{ color: "#64748b", width: 48 }}>IBAN</span>
                  <span className="text-xs font-mono" style={{ color: "#94a3b8" }}>{party.iban}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Dates & Amounts */}
      <div
        className="rounded-xl p-4 grid grid-cols-4 gap-4"
        style={{ background: "#1e293b", border: "1px solid #334155" }}
      >
        {[
          { label: "Issue Date", value: formatDate(invoice.issue_date) },
          { label: "Due Date", value: formatDate(invoice.due_date) },
          { label: "Payment Terms", value: invoice.payment_terms || "—" },
          { label: "Currency", value: invoice.currency },
        ].map((item) => (
          <div key={item.label}>
            <p className="text-xs" style={{ color: "#64748b" }}>{item.label}</p>
            <p className="text-sm font-medium mt-1" style={{ color: "#f1f5f9" }}>{item.value}</p>
          </div>
        ))}
      </div>

      {/* Tax Subtotals */}
      {invoice.tax_subtotals && invoice.tax_subtotals.length > 0 && (
        <div
          className="rounded-xl overflow-hidden"
          style={{ background: "#1e293b", border: "1px solid #334155" }}
        >
          <div className="px-4 py-3" style={{ borderBottom: "1px solid #334155" }}>
            <h3 className="text-sm font-semibold" style={{ color: "#f1f5f9" }}>Tax Subtotals</h3>
          </div>
          <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #334155" }}>
                {["Category", "Rate", "Taxable Amount", "VAT Amount"].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-2.5 text-left text-xs font-semibold uppercase"
                    style={{ color: "#64748b" }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {invoice.tax_subtotals.map((t, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #1e293b" }}>
                  <td className="px-4 py-3" style={{ color: "#94a3b8" }}>{t.tax_category}</td>
                  <td className="px-4 py-3 font-mono" style={{ color: "#f1f5f9" }}>{t.tax_rate}%</td>
                  <td className="px-4 py-3 text-right" style={{ color: "#f1f5f9" }}>
                    {formatEur(t.taxable_amount, invoice.currency)}
                  </td>
                  <td className="px-4 py-3 text-right font-medium" style={{ color: "#f59e0b" }}>
                    {formatEur(t.tax_amount, invoice.currency)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Invoice Lines */}
      {invoice.lines && invoice.lines.length > 0 && (
        <div
          className="rounded-xl overflow-hidden"
          style={{ background: "#1e293b", border: "1px solid #334155" }}
        >
          <div className="px-4 py-3" style={{ borderBottom: "1px solid #334155" }}>
            <h3 className="text-sm font-semibold" style={{ color: "#f1f5f9" }}>
              Invoice Lines ({invoice.lines.length})
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #334155" }}>
                  {["#", "Description", "Qty", "Unit Price", "Line Amount", "VAT%"].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-2.5 text-left text-xs font-semibold uppercase"
                      style={{ color: "#64748b" }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {invoice.lines.map((line) => (
                  <tr key={line.line_number} style={{ borderBottom: "1px solid #1e293b" }}>
                    <td className="px-4 py-3 font-mono text-xs" style={{ color: "#64748b" }}>
                      {line.line_number}
                    </td>
                    <td className="px-4 py-3" style={{ color: "#f1f5f9", maxWidth: 300 }}>
                      {line.description}
                    </td>
                    <td className="px-4 py-3 font-mono" style={{ color: "#94a3b8" }}>
                      {line.quantity} {line.unit || ""}
                    </td>
                    <td className="px-4 py-3 text-right" style={{ color: "#94a3b8" }}>
                      {formatEur(line.unit_price, invoice.currency)}
                    </td>
                    <td className="px-4 py-3 text-right font-medium" style={{ color: "#f1f5f9" }}>
                      {formatEur(line.line_amount, invoice.currency)}
                    </td>
                    <td className="px-4 py-3 font-mono" style={{ color: "#f59e0b" }}>
                      {line.vat_rate}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Anomalies */}
      {invoice.anomalies && invoice.anomalies.length > 0 && (
        <div
          className="rounded-xl overflow-hidden"
          style={{ background: "#1e293b", border: "1px solid #334155" }}
        >
          <div className="px-4 py-3" style={{ borderBottom: "1px solid #334155" }}>
            <h3 className="text-sm font-semibold" style={{ color: "#f87171" }}>
              Anomalies Detected ({invoice.anomalies.length})
            </h3>
          </div>
          <div className="divide-y" style={{ borderColor: "#334155" }}>
            {invoice.anomalies.map((a) => {
              const s = SEVERITY_STYLE[a.severity] || SEVERITY_STYLE.low;
              return (
                <div
                  key={a.id}
                  className="px-4 py-4 flex items-start gap-3"
                  style={{ borderLeft: `3px solid ${s.border}` }}
                >
                  <AlertTriangle size={16} color={s.color} className="mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className="text-xs font-semibold px-1.5 py-0.5 rounded"
                        style={{ background: s.bg, color: s.color }}
                      >
                        {a.severity.toUpperCase()}
                      </span>
                      <span className="text-xs" style={{ color: "#64748b" }}>
                        {a.category.replace(/_/g, " ")}
                      </span>
                    </div>
                    <p className="text-sm" style={{ color: "#f1f5f9" }}>{a.message}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
