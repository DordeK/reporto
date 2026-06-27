"use client";

import { useEffect, useState, useCallback } from "react";
import { listAnomalies, Anomaly } from "@/lib/api";
import AnomalyList from "@/components/anomalies/AnomalyList";
import { AlertTriangle } from "lucide-react";

type Filter = "all" | "high" | "medium" | "low";

const FILTERS: { id: Filter; label: string; color: string }[] = [
  { id: "all", label: "All", color: "#94a3b8" },
  { id: "high", label: "High", color: "#f87171" },
  { id: "medium", label: "Medium", color: "#fbbf24" },
  { id: "low", label: "Low", color: "#60a5fa" },
];

export default function AnomaliesPage() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listAnomalies();
      setAnomalies(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load anomalies");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const counts = {
    all: anomalies.length,
    high: anomalies.filter((a) => a.severity === "high").length,
    medium: anomalies.filter((a) => a.severity === "medium").length,
    low: anomalies.filter((a) => a.severity === "low").length,
  };

  const filtered = filter === "all" ? anomalies : anomalies.filter((a) => a.severity === filter);

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-1">
          <h1
            className="text-2xl font-bold"
            style={{ color: "#f1f5f9", letterSpacing: "-0.02em" }}
          >
            Anomaly Center
          </h1>
          {counts.all > 0 && (
            <span
              className="text-xs font-bold px-2 py-1 rounded-full"
              style={{ background: "rgba(239,68,68,0.15)", color: "#f87171" }}
            >
              {counts.all}
            </span>
          )}
        </div>
        <p className="text-sm" style={{ color: "#64748b" }}>
          Invoice compliance issues detected by AI
        </p>

        {/* Severity breakdown */}
        {!loading && counts.all > 0 && (
          <div className="flex items-center gap-4 mt-3">
            <div className="flex items-center gap-1.5">
              <AlertTriangle size={13} color="#f87171" />
              <span className="text-sm font-semibold" style={{ color: "#f87171" }}>
                {counts.high}
              </span>
              <span className="text-sm" style={{ color: "#64748b" }}>
                high
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <AlertTriangle size={13} color="#fbbf24" />
              <span className="text-sm font-semibold" style={{ color: "#fbbf24" }}>
                {counts.medium}
              </span>
              <span className="text-sm" style={{ color: "#64748b" }}>
                medium
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <AlertTriangle size={13} color="#60a5fa" />
              <span className="text-sm font-semibold" style={{ color: "#60a5fa" }}>
                {counts.low}
              </span>
              <span className="text-sm" style={{ color: "#64748b" }}>
                low
              </span>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div
          className="rounded-lg px-4 py-3 mb-4 text-sm"
          style={{
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            color: "#fca5a5",
          }}
        >
          {error}
        </div>
      )}

      {/* Filter buttons */}
      <div className="flex gap-2 mb-5">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
            style={{
              background: filter === f.id ? `${f.color}20` : "transparent",
              border: `1px solid ${filter === f.id ? `${f.color}50` : "#334155"}`,
              color: filter === f.id ? f.color : "#64748b",
              cursor: "pointer",
            }}
          >
            {f.label}
            <span
              className="text-xs px-1.5 py-0.5 rounded-full"
              style={{
                background: filter === f.id ? `${f.color}30` : "#334155",
                color: filter === f.id ? f.color : "#64748b",
              }}
            >
              {counts[f.id]}
            </span>
          </button>
        ))}
      </div>

      <AnomalyList anomalies={filtered} loading={loading} />
    </div>
  );
}
