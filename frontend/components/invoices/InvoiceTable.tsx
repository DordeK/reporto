"use client";

import { Invoice } from "@/lib/api";
import { useRouter } from "next/navigation";
import { Eye, ChevronLeft, ChevronRight } from "lucide-react";

interface InvoiceTableProps {
  invoices: Invoice[];
  total: number;
  page: number;
  pages: number;
  onPageChange: (p: number) => void;
  loading?: boolean;
}

const formatEur = (v: number, currency = "EUR") =>
  new Intl.NumberFormat("en-EU", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(v);

const formatDate = (d: string) => {
  try {
    return new Date(d).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return d;
  }
};

const SOURCE_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  upload: { bg: "rgba(59,130,246,0.15)", color: "#60a5fa", label: "Upload" },
  email: { bg: "rgba(34,197,94,0.15)", color: "#4ade80", label: "Email" },
  provider: { bg: "rgba(168,85,247,0.15)", color: "#c084fc", label: "Provider" },
};

export default function InvoiceTable({
  invoices,
  total,
  page,
  pages,
  onPageChange,
  loading,
}: InvoiceTableProps) {
  const router = useRouter();

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #334155" }}>
              {[
                "Invoice #",
                "Supplier",
                "Customer",
                "Issue Date",
                "Total",
                "VAT",
                "Currency",
                "Source",
                "Anomalies",
                "",
              ].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider"
                  style={{ color: "#64748b" }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading &&
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #1e293b" }}>
                  {Array.from({ length: 10 }).map((__, j) => (
                    <td key={j} className="px-4 py-3">
                      <div
                        className="h-4 rounded animate-pulse"
                        style={{ background: "#334155", width: j === 0 ? 80 : j === 9 ? 32 : "100%" }}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            {!loading && invoices.length === 0 && (
              <tr>
                <td
                  colSpan={10}
                  className="px-4 py-12 text-center text-sm"
                  style={{ color: "#64748b" }}
                >
                  No invoices found.
                </td>
              </tr>
            )}
            {!loading &&
              invoices.map((inv) => {
                const src = SOURCE_STYLE[inv.source] || SOURCE_STYLE.upload;
                return (
                  <tr
                    key={inv.id}
                    className="transition-colors cursor-pointer"
                    style={{ borderBottom: "1px solid #1e293b" }}
                    onMouseEnter={(e) =>
                      ((e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.03)")
                    }
                    onMouseLeave={(e) =>
                      ((e.currentTarget as HTMLElement).style.background = "transparent")
                    }
                    onClick={() => router.push(`/invoices/${inv.id}`)}
                  >
                    <td className="px-4 py-3">
                      <span style={{ color: "#60a5fa", fontFamily: "monospace", fontSize: 12 }}>
                        {inv.invoice_number}
                      </span>
                    </td>
                    <td className="px-4 py-3" style={{ color: "#f1f5f9" }}>
                      {inv.supplier_name}
                    </td>
                    <td className="px-4 py-3" style={{ color: "#94a3b8" }}>
                      {inv.customer_name}
                    </td>
                    <td className="px-4 py-3" style={{ color: "#94a3b8" }}>
                      {formatDate(inv.issue_date)}
                    </td>
                    <td className="px-4 py-3 text-right font-medium" style={{ color: "#f1f5f9" }}>
                      {formatEur(inv.payable_amount ?? 0, inv.currency)}
                    </td>
                    <td className="px-4 py-3 text-right" style={{ color: "#94a3b8" }}>
                      {formatEur(inv.tax_amount ?? 0, inv.currency)}
                    </td>
                    <td className="px-4 py-3" style={{ color: "#64748b" }}>
                      {inv.currency}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="text-xs font-medium px-2 py-1 rounded-full"
                        style={{ background: src.bg, color: src.color }}
                      >
                        {src.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {inv.anomaly_count > 0 ? (
                        <span
                          className="text-xs font-bold px-2 py-1 rounded-full"
                          style={{ background: "rgba(239,68,68,0.15)", color: "#f87171" }}
                        >
                          {inv.anomaly_count}
                        </span>
                      ) : (
                        <span className="text-xs" style={{ color: "#334155" }}>
                          —
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          router.push(`/invoices/${inv.id}`);
                        }}
                        className="flex items-center justify-center rounded-lg transition-colors"
                        style={{
                          width: 30,
                          height: 30,
                          background: "rgba(59,130,246,0.1)",
                          border: "none",
                          cursor: "pointer",
                        }}
                      >
                        <Eye size={14} color="#3b82f6" />
                      </button>
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {!loading && total > 0 && (
        <div
          className="flex items-center justify-between px-4 py-3"
          style={{ borderTop: "1px solid #334155" }}
        >
          <span className="text-xs" style={{ color: "#64748b" }}>
            Showing {invoices.length} of {total} invoices
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium transition-colors"
              style={{
                background: page > 1 ? "rgba(59,130,246,0.1)" : "transparent",
                color: page > 1 ? "#3b82f6" : "#334155",
                border: "1px solid",
                borderColor: page > 1 ? "rgba(59,130,246,0.3)" : "#334155",
                cursor: page > 1 ? "pointer" : "not-allowed",
              }}
            >
              <ChevronLeft size={12} />
              Previous
            </button>
            <span className="text-xs px-2" style={{ color: "#64748b" }}>
              {page} / {pages}
            </span>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= pages}
              className="flex items-center gap-1 px-3 py-1.5 rounded text-xs font-medium transition-colors"
              style={{
                background: page < pages ? "rgba(59,130,246,0.1)" : "transparent",
                color: page < pages ? "#3b82f6" : "#334155",
                border: "1px solid",
                borderColor: page < pages ? "rgba(59,130,246,0.3)" : "#334155",
                cursor: page < pages ? "pointer" : "not-allowed",
              }}
            >
              Next
              <ChevronRight size={12} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
