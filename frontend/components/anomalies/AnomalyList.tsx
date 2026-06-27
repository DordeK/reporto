"use client";

import { Anomaly } from "@/lib/api";
import { AlertTriangle, CheckCircle } from "lucide-react";
import Link from "next/link";

interface AnomalyListProps {
  anomalies: Anomaly[];
  loading?: boolean;
}

const SEVERITY_STYLE: Record<
  string,
  { bg: string; color: string; border: string; label: string }
> = {
  high: { bg: "rgba(239,68,68,0.05)", color: "#f87171", border: "#ef4444", label: "High" },
  medium: { bg: "rgba(245,158,11,0.05)", color: "#fbbf24", border: "#f59e0b", label: "Medium" },
  low: { bg: "rgba(59,130,246,0.05)", color: "#60a5fa", border: "#3b82f6", label: "Low" },
};

function formatDate(d: string): string {
  try {
    return new Date(d).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return d;
  }
}

function formatCategory(cat: string): string {
  return cat
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function AnomalyList({ anomalies, loading }: AnomalyListProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="rounded-xl px-4 py-4 animate-pulse"
            style={{ background: "#1e293b", border: "1px solid #334155", borderLeft: "3px solid #334155" }}
          >
            <div className="flex items-center gap-3 mb-2">
              <div className="h-5 w-12 rounded" style={{ background: "#334155" }} />
              <div className="h-4 w-24 rounded" style={{ background: "#334155" }} />
            </div>
            <div className="h-4 w-3/4 rounded" style={{ background: "#334155" }} />
          </div>
        ))}
      </div>
    );
  }

  if (anomalies.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div
          className="flex items-center justify-center rounded-2xl mb-4"
          style={{ width: 60, height: 60, background: "rgba(34,197,94,0.1)" }}
        >
          <CheckCircle size={28} color="#22c55e" />
        </div>
        <h3 className="text-base font-semibold mb-1" style={{ color: "#f1f5f9" }}>
          No anomalies detected
        </h3>
        <p className="text-sm" style={{ color: "#64748b" }}>
          All invoices are passing compliance checks.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {anomalies.map((a) => {
        const s = SEVERITY_STYLE[a.severity] || SEVERITY_STYLE.low;
        return (
          <div
            key={a.id}
            className="rounded-xl px-5 py-4"
            style={{
              background: s.bg,
              border: `1px solid ${s.border}25`,
              borderLeft: `3px solid ${s.border}`,
            }}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3 flex-1 min-w-0">
                <AlertTriangle size={16} color={s.color} className="mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span
                      className="text-xs font-bold px-2 py-0.5 rounded"
                      style={{ background: `${s.border}25`, color: s.color }}
                    >
                      {s.label}
                    </span>
                    <span className="text-xs font-medium" style={{ color: "#94a3b8" }}>
                      {formatCategory(a.category)}
                    </span>
                    {a.invoice_number && (
                      <Link
                        href={`/invoices/${a.invoice_id}`}
                        className="text-xs font-mono transition-colors"
                        style={{ color: "#60a5fa", textDecoration: "none" }}
                      >
                        {a.invoice_number}
                      </Link>
                    )}
                  </div>
                  <p className="text-sm" style={{ color: "#f1f5f9", lineHeight: 1.5 }}>
                    {a.message}
                  </p>
                </div>
              </div>
              <span className="text-xs flex-shrink-0" style={{ color: "#475569" }}>
                {formatDate(a.detected_at)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
