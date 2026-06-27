"use client";

import { ReportRun } from "@/lib/api";
import { FileBarChart } from "lucide-react";
import Link from "next/link";

interface RecentReportsProps {
  reports: ReportRun[];
  loading?: boolean;
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

export default function RecentReports({ reports, loading }: RecentReportsProps) {
  return (
    <div
      className="rounded-xl"
      style={{ background: "#1e293b", border: "1px solid #334155" }}
    >
      <div
        className="flex items-center justify-between px-5 py-4"
        style={{ borderBottom: "1px solid #334155" }}
      >
        <h3 className="text-sm font-semibold" style={{ color: "#f1f5f9" }}>
          Recent Reports
        </h3>
        <Link
          href="/reports"
          className="text-xs font-medium transition-colors"
          style={{ color: "#3b82f6", textDecoration: "none" }}
        >
          View all →
        </Link>
      </div>
      <div className="divide-y" style={{ borderColor: "#334155" }}>
        {loading &&
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="px-5 py-3 animate-pulse flex items-center gap-3">
              <div className="w-8 h-8 rounded" style={{ background: "#334155" }} />
              <div className="flex-1">
                <div className="h-3 rounded w-3/4 mb-2" style={{ background: "#334155" }} />
                <div className="h-2 rounded w-1/4" style={{ background: "#334155" }} />
              </div>
            </div>
          ))}
        {!loading && reports.length === 0 && (
          <div className="px-5 py-8 text-center text-sm" style={{ color: "#64748b" }}>
            No reports generated yet.{" "}
            <Link href="/reports" style={{ color: "#3b82f6", textDecoration: "none" }}>
              Create your first report
            </Link>
          </div>
        )}
        {!loading &&
          reports.slice(0, 5).map((r) => (
            <div key={r.id} className="flex items-center gap-3 px-5 py-3">
              <div
                className="flex items-center justify-center rounded-lg flex-shrink-0"
                style={{ width: 34, height: 34, background: "rgba(59,130,246,0.15)" }}
              >
                <FileBarChart size={16} color="#3b82f6" />
              </div>
              <div className="flex-1 min-w-0">
                <p
                  className="text-sm font-medium truncate"
                  style={{ color: "#f1f5f9" }}
                  title={r.prompt}
                >
                  {r.report_name || r.prompt}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs" style={{ color: "#64748b" }}>
                    {formatDate(r.created_at)}
                  </span>
                  {r.row_count !== undefined && (
                    <span className="text-xs" style={{ color: "#64748b" }}>
                      · {r.row_count} rows
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
      </div>
    </div>
  );
}
