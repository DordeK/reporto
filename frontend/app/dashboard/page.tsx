"use client";

import { useEffect, useState } from "react";
import {
  FileText,
  Receipt,
  AlertTriangle,
  MessageSquare,
} from "lucide-react";
import Link from "next/link";
import { getDashboardStats, listReports, DashboardStats, ReportRun } from "@/lib/api";
import StatsCard from "@/components/dashboard/StatsCard";
import { VatBarChart, SourcePieChart } from "@/components/dashboard/VatChart";
import RecentReports from "@/components/dashboard/RecentReports";

const formatEur = (v: number) =>
  new Intl.NumberFormat("en-EU", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(v);

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [reports, setReports] = useState<ReportRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getDashboardStats(), listReports()])
      .then(([s, r]) => {
        setStats(s);
        setReports(r);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold" style={{ color: "#f1f5f9", letterSpacing: "-0.02em" }}>
          Dashboard
        </h1>
        <p className="text-sm mt-1" style={{ color: "#64748b" }}>
          E-Invoicing compliance overview
        </p>
      </div>

      {error && (
        <div
          className="rounded-lg px-4 py-3 mb-6 text-sm"
          style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#fca5a5" }}
        >
          Failed to load dashboard data: {error}
        </div>
      )}

      {/* Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <StatsCard
          title="Total Invoices"
          value={stats?.totalInvoices ?? 0}
          icon={FileText}
          color="#3b82f6"
          subtitle="All time"
          loading={loading}
        />
        <StatsCard
          title="Total VAT"
          value={stats ? formatEur(stats.totalVat) : "—"}
          icon={Receipt}
          color="#f59e0b"
          subtitle="VAT collected"
          loading={loading}
        />
        <StatsCard
          title="Anomalies"
          value={stats?.anomalyCount ?? 0}
          icon={AlertTriangle}
          color={stats && stats.anomalyCount > 0 ? "#ef4444" : "#22c55e"}
          subtitle={stats?.anomalyCount === 0 ? "All clear" : "Require review"}
          loading={loading}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <VatBarChart vatByRate={stats?.vatByRate ?? []} loading={loading} />
        <SourcePieChart bySource={stats?.invoicesBySource ?? { upload: 0 }} loading={loading} />
      </div>

      {/* Bottom Row: Recent Reports + Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <RecentReports reports={reports} loading={loading} />
        </div>

        {/* Quick Actions */}
        <div className="flex flex-col gap-3">
          <h3 className="text-sm font-semibold px-1" style={{ color: "#94a3b8" }}>
            Quick Actions
          </h3>
          <Link
            href="/reports"
            className="flex items-center gap-3 rounded-xl px-4 py-4 transition-all duration-150 hover:translate-y-[-1px]"
            style={{
              background: "rgba(168,85,247,0.1)",
              border: "1px solid rgba(168,85,247,0.3)",
              textDecoration: "none",
            }}
          >
            <div
              className="flex items-center justify-center rounded-lg"
              style={{ width: 38, height: 38, background: "rgba(168,85,247,0.2)" }}
            >
              <MessageSquare size={18} color="#a855f7" />
            </div>
            <div>
              <p className="text-sm font-semibold" style={{ color: "#f1f5f9" }}>
                Generate Report
              </p>
              <p className="text-xs" style={{ color: "#64748b" }}>
                AI-powered analysis
              </p>
            </div>
          </Link>

          <Link
            href="/anomalies"
            className="flex items-center gap-3 rounded-xl px-4 py-4 transition-all duration-150 hover:translate-y-[-1px]"
            style={{
              background: "rgba(239,68,68,0.1)",
              border: "1px solid rgba(239,68,68,0.3)",
              textDecoration: "none",
            }}
          >
            <div
              className="flex items-center justify-center rounded-lg"
              style={{ width: 38, height: 38, background: "rgba(239,68,68,0.2)" }}
            >
              <AlertTriangle size={18} color="#ef4444" />
            </div>
            <div>
              <p className="text-sm font-semibold" style={{ color: "#f1f5f9" }}>
                View Anomalies
              </p>
              <p className="text-xs" style={{ color: "#64748b" }}>
                {stats?.anomalyCount
                  ? `${stats.anomalyCount} issues detected`
                  : "Check compliance"}
              </p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
