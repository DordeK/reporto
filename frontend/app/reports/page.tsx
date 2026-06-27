"use client";

import { useState, useCallback } from "react";
import {
  generateReport,
  generateBelgianVatReturn,
  ReportResult,
} from "@/lib/api";
import ReportChat, { ChatMessage } from "@/components/reports/ReportChat";
import ReportChart from "@/components/reports/ReportChart";
import ReportDefinitionPanel from "@/components/reports/ReportDefinitionPanel";
import DatasetCompleteness from "@/components/reports/DatasetCompleteness";
import DataQualityScore from "@/components/reports/DataQualityScore";
import ValidationPanel from "@/components/reports/ValidationPanel";
import DrilldownModal from "@/components/reports/DrilldownModal";
import { AlertTriangle, Sparkles, Download } from "lucide-react";

type ReportTab = "results" | "explanation" | "definition" | "validation";

let msgCounter = 0;
const newId = () => `msg-${++msgCounter}-${Date.now()}`;

const SEVERITY_STYLE: Record<string, { bg: string; color: string; border: string }> = {
  high: { bg: "rgba(239,68,68,0.1)", color: "#f87171", border: "#ef4444" },
  medium: { bg: "rgba(245,158,11,0.1)", color: "#fbbf24", border: "#f59e0b" },
  low: { bg: "rgba(59,130,246,0.1)", color: "#60a5fa", border: "#3b82f6" },
};

const BELGIAN_VAT_KEYWORDS = ["belgian vat return", "belgian vat", "vat return", "intervat"];

function isBelgianVatPrompt(prompt: string): boolean {
  const lower = prompt.toLowerCase();
  return BELGIAN_VAT_KEYWORDS.some((kw) => lower.includes(kw));
}

// Belgian VAT Return form component
interface VatFormData {
  period_start: string;
  period_end: string;
  declarant_vat: string;
  declarant_name: string;
  declarant_street: string;
  declarant_city: string;
  declarant_postal: string;
  declarant_email: string;
}

interface BelgianVatResult {
  period_start: string;
  period_end: string;
  grids: Record<string, number>;
  xml: string;
  format: string;
  warnings: string[];
}

function BelgianVatPanel({ onClose }: { onClose: () => void }) {
  const [form, setForm] = useState<VatFormData>({
    period_start: "2025-01-01",
    period_end: "2025-03-31",
    declarant_vat: "",
    declarant_name: "",
    declarant_street: "",
    declarant_city: "",
    declarant_postal: "",
    declarant_email: "",
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BelgianVatResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (field: keyof VatFormData) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await generateBelgianVatReturn(form);
      setResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!result?.xml) return;
    const blob = new Blob([result.xml], { type: "application/xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `belgian-vat-return-${result.period_start}-${result.period_end}.xml`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const GRID_LABELS: Record<string, string> = {
    "02": "Sales (6% / 12%)",
    "03": "Sales (21%)",
    "46": "IC Sales",
    "49": "Other operations",
    "54": "VAT due on sales",
    "59": "VAT deductible",
    "81": "Purchases / services",
    "85": "Services",
    "88": "IC Purchases",
    "71": "VAT payable",
    "72": "VAT refund due",
  };

  const inputStyle = {
    background: "#0f172a",
    border: "1px solid #334155",
    color: "#f1f5f9",
    borderRadius: 8,
    padding: "8px 12px",
    fontSize: 13,
    width: "100%",
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: "1px solid #334155" }}>
        <h2 className="text-lg font-bold" style={{ color: "#f1f5f9" }}>Belgian VAT Return</h2>
        <button
          onClick={onClose}
          style={{ background: "none", border: "none", cursor: "pointer", color: "#64748b", fontSize: 20 }}
        >
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {error && (
          <div className="rounded-lg px-4 py-3 text-sm" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#fca5a5" }}>
            {error}
          </div>
        )}

        {!result ? (
          <>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs mb-1" style={{ color: "#64748b" }}>Period Start</label>
                <input type="date" value={form.period_start} onChange={handleChange("period_start")} style={inputStyle} />
              </div>
              <div>
                <label className="block text-xs mb-1" style={{ color: "#64748b" }}>Period End</label>
                <input type="date" value={form.period_end} onChange={handleChange("period_end")} style={inputStyle} />
              </div>
            </div>
            <div>
              <label className="block text-xs mb-1" style={{ color: "#64748b" }}>Company VAT Number</label>
              <input type="text" placeholder="BE0123456789" value={form.declarant_vat} onChange={handleChange("declarant_vat")} style={inputStyle} />
            </div>
            <div>
              <label className="block text-xs mb-1" style={{ color: "#64748b" }}>Company Name</label>
              <input type="text" value={form.declarant_name} onChange={handleChange("declarant_name")} style={inputStyle} />
            </div>
            <div>
              <label className="block text-xs mb-1" style={{ color: "#64748b" }}>Street</label>
              <input type="text" value={form.declarant_street} onChange={handleChange("declarant_street")} style={inputStyle} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs mb-1" style={{ color: "#64748b" }}>City</label>
                <input type="text" value={form.declarant_city} onChange={handleChange("declarant_city")} style={inputStyle} />
              </div>
              <div>
                <label className="block text-xs mb-1" style={{ color: "#64748b" }}>Postal Code</label>
                <input type="text" value={form.declarant_postal} onChange={handleChange("declarant_postal")} style={inputStyle} />
              </div>
            </div>
            <div>
              <label className="block text-xs mb-1" style={{ color: "#64748b" }}>Email</label>
              <input type="email" value={form.declarant_email} onChange={handleChange("declarant_email")} style={inputStyle} />
            </div>

            <button
              onClick={handleGenerate}
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold w-full justify-center"
              style={{
                background: !loading ? "#3b82f6" : "#334155",
                color: !loading ? "#fff" : "#64748b",
                border: "none",
                cursor: !loading ? "pointer" : "not-allowed",
              }}
            >
              {loading ? "Generating…" : "Generate Official Return"}
            </button>
          </>
        ) : (
          <>
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-semibold" style={{ color: "#4ade80" }}>
                VAT Return Generated — {result.period_start} to {result.period_end}
              </p>
              <button
                onClick={handleDownload}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium"
                style={{ background: "rgba(59,130,246,0.15)", color: "#60a5fa", border: "1px solid rgba(59,130,246,0.3)", cursor: "pointer" }}
              >
                <Download size={12} /> Download Intervat XML
              </button>
            </div>

            {result.warnings.length > 0 && (
              <div className="rounded-lg p-3" style={{ background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)" }}>
                {result.warnings.map((w, i) => (
                  <p key={i} className="text-xs" style={{ color: "#fbbf24" }}>⚠ {w}</p>
                ))}
              </div>
            )}

            <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #334155" }}>
              <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "#0f172a", borderBottom: "1px solid #334155" }}>
                    <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: "#64748b" }}>Grid</th>
                    <th className="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: "#64748b" }}>Description</th>
                    <th className="px-4 py-2 text-right text-xs font-semibold uppercase tracking-wider" style={{ color: "#64748b" }}>Amount (EUR)</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(result.grids).map(([grid, amount], i) => (
                    <tr key={grid} style={{ borderBottom: "1px solid #1e293b", background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.01)" }}>
                      <td className="px-4 py-2.5 font-mono text-xs" style={{ color: "#60a5fa" }}>{grid}</td>
                      <td className="px-4 py-2.5 text-xs" style={{ color: "#94a3b8" }}>{GRID_LABELS[grid] ?? ""}</td>
                      <td className="px-4 py-2.5 text-right font-mono" style={{ color: "#f1f5f9" }}>
                        {typeof amount === "number"
                          ? new Intl.NumberFormat("en-BE", { style: "currency", currency: "EUR" }).format(amount)
                          : amount}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <button
              onClick={() => setResult(null)}
              className="text-xs px-3 py-1.5 rounded-lg"
              style={{ background: "#334155", color: "#94a3b8", border: "none", cursor: "pointer" }}
            >
              Generate another
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// Clickable report table with drilldown
function DrillableReportTable({
  rows,
  groupByFields,
  onRowClick,
}: {
  rows: Record<string, unknown>[];
  groupByFields: string[];
  onRowClick: (row: Record<string, unknown>) => void;
}) {
  if (!rows || rows.length === 0) {
    return (
      <div
        className="rounded-lg px-4 py-8 text-center text-sm"
        style={{ background: "#0f172a", border: "1px solid #334155", color: "#64748b" }}
      >
        No data returned
      </div>
    );
  }

  const columns = Object.keys(rows[0]);
  const hasGroupBy = groupByFields.length > 0;

  function formatValue(v: unknown): string {
    if (v === null || v === undefined) return "—";
    if (typeof v === "number") {
      if (v > 1000 || v < -1000) {
        return new Intl.NumberFormat("en-EU", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(v);
      }
      return v.toLocaleString("en-EU", { maximumFractionDigits: 4 });
    }
    if (typeof v === "string") {
      if (/^\d{4}-\d{2}-\d{2}/.test(v)) {
        try {
          return new Date(v).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
        } catch {
          return v;
        }
      }
      return v;
    }
    return String(v);
  }

  return (
    <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #334155" }}>
      <div className="overflow-x-auto">
        <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#0f172a", borderBottom: "1px solid #334155" }}>
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-4 py-2.5 text-xs font-semibold uppercase tracking-wider"
                  style={{
                    color: "#64748b",
                    textAlign: rows.some((r) => typeof r[col] === "number") ? "right" : "left",
                  }}
                >
                  {col.replace(/_/g, " ")}
                </th>
              ))}
              {hasGroupBy && <th className="px-4 py-2.5" />}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={i}
                onClick={() => onRowClick(row)}
                style={{
                  borderBottom: i < rows.length - 1 ? "1px solid #1e293b" : "none",
                  background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.01)",
                  cursor: "pointer",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.background = "rgba(59,130,246,0.08)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.background =
                    i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.01)";
                }}
              >
                {columns.map((col) => {
                  const isNum = typeof row[col] === "number";
                  return (
                    <td
                      key={col}
                      className="px-4 py-3"
                      style={{
                        color: isNum ? "#f1f5f9" : "#94a3b8",
                        textAlign: isNum ? "right" : "left",
                        fontFamily: isNum ? "monospace" : "inherit",
                        fontWeight: isNum ? 500 : 400,
                      }}
                    >
                      {formatValue(row[col])}
                    </td>
                  );
                })}
                {hasGroupBy && (
                  <td className="px-4 py-3 text-right">
                    <span className="text-xs" style={{ color: "#3b82f6" }}>↗</span>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div
        className="px-4 py-2 text-xs"
        style={{ background: "#0f172a", borderTop: "1px solid #334155", color: "#475569" }}
      >
        {rows.length} row{rows.length !== 1 ? "s" : ""} · Click a row to drill down
      </div>
    </div>
  );
}

export default function ReportsPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeReport, setActiveReport] = useState<ReportResult | null>(null);
  const [activeTab, setActiveTab] = useState<ReportTab>("results");
  const [showBelgianVat, setShowBelgianVat] = useState(false);

  // Drilldown state
  const [drilldownRow, setDrilldownRow] = useState<{
    runId: string;
    groupKey: Record<string, any>;
    groupLabel: string;
  } | null>(null);

  const handleSubmit = useCallback(async (prompt: string) => {
    // Intercept Belgian VAT prompt
    if (isBelgianVatPrompt(prompt)) {
      setShowBelgianVat(true);
      const userMsgId = newId();
      const aiMsgId = newId();
      setMessages((prev) => [
        ...prev,
        { id: userMsgId, role: "user", content: prompt },
        {
          id: aiMsgId,
          role: "assistant",
          content: "Opening Belgian VAT Return form. Please fill in the declarant details on the right.",
          loading: false,
        },
      ]);
      return;
    }

    const userMsgId = newId();
    const aiMsgId = newId();

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: "user", content: prompt },
      { id: aiMsgId, role: "assistant", content: "", loading: true },
    ]);
    setLoading(true);

    try {
      const result = await generateReport(prompt);

      const summary =
        result.reportDefinition?.name
          ? `Generated "${result.reportDefinition.name}" — ${result.rows?.length ?? 0} rows returned.`
          : `Report complete — ${result.rows?.length ?? 0} rows returned.`;

      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiMsgId
            ? { ...m, content: summary, loading: false, result }
            : m
        )
      );
      setActiveReport(result);
      setActiveTab("results");
      setShowBelgianVat(false);
    } catch (e: unknown) {
      const errMsg = e instanceof Error ? e.message : "Report generation failed";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiMsgId
            ? { ...m, content: "", loading: false, error: errMsg }
            : m
        )
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRowClick = (row: Record<string, unknown>) => {
    if (!activeReport?.reportRunId) return;
    const groupByFields = activeReport.reportDefinition?.group_by ?? [];
    const groupKey = groupByFields.reduce<Record<string, any>>((acc, field) => {
      if (row[field] !== undefined) acc[field] = row[field];
      return acc;
    }, {});
    const labelParts = groupByFields.map((f) => String(row[f] ?? "")).filter(Boolean);
    setDrilldownRow({
      runId: activeReport.reportRunId,
      groupKey,
      groupLabel: labelParts.join(" / ") || "Selected row",
    });
  };

  const TABS: { id: ReportTab; label: string }[] = [
    { id: "results", label: "Results" },
    { id: "explanation", label: "Explanation" },
    { id: "definition", label: "Definition" },
    { id: "validation", label: "Validation" },
  ];

  return (
    <div className="flex h-full" style={{ height: "calc(100vh - 0px)" }}>
      {/* Left Panel: Chat (40%) */}
      <div
        className="flex flex-col"
        style={{
          width: "40%",
          borderRight: "1px solid #334155",
          height: "100vh",
          position: "sticky",
          top: 0,
        }}
      >
        {/* Header */}
        <div
          className="px-5 py-4 flex items-center gap-2"
          style={{ borderBottom: "1px solid #334155" }}
        >
          <div
            className="flex items-center justify-center rounded-lg"
            style={{ width: 32, height: 32, background: "rgba(168,85,247,0.15)" }}
          >
            <Sparkles size={16} color="#a855f7" />
          </div>
          <div>
            <h1 className="text-sm font-bold" style={{ color: "#f1f5f9" }}>
              Report Assistant
            </h1>
            <p className="text-xs" style={{ color: "#64748b" }}>
              AI-powered invoice analysis
            </p>
          </div>
        </div>

        <div className="flex-1 overflow-hidden">
          <ReportChat
            messages={messages}
            onSubmit={handleSubmit}
            onSelectReport={(r) => {
              setActiveReport(r);
              setActiveTab("results");
              setShowBelgianVat(false);
            }}
            loading={loading}
          />
        </div>
      </div>

      {/* Right Panel: Report Display (60%) */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {showBelgianVat ? (
          <BelgianVatPanel onClose={() => setShowBelgianVat(false)} />
        ) : !activeReport ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div
                className="flex items-center justify-center rounded-2xl mx-auto mb-4"
                style={{ width: 64, height: 64, background: "rgba(59,130,246,0.1)" }}
              >
                <Sparkles size={28} color="#3b82f6" />
              </div>
              <h2 className="text-lg font-semibold mb-2" style={{ color: "#f1f5f9" }}>
                Your report will appear here
              </h2>
              <p className="text-sm max-w-sm" style={{ color: "#64748b" }}>
                Ask the assistant on the left to generate a report, and the results will be
                displayed here with charts, data tables, and explanations.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col h-full">
            {/* Report Header */}
            <div
              className="px-6 py-4 flex items-start justify-between"
              style={{ borderBottom: "1px solid #334155" }}
            >
              <div>
                <h2 className="text-lg font-bold" style={{ color: "#f1f5f9", letterSpacing: "-0.01em" }}>
                  {activeReport.reportDefinition?.name || "Report Results"}
                </h2>
                {activeReport.reportDefinition?.description && (
                  <p className="text-sm mt-0.5" style={{ color: "#64748b" }}>
                    {activeReport.reportDefinition.description}
                  </p>
                )}
              </div>
              <div
                className="text-xs px-2.5 py-1 rounded-full font-medium"
                style={{ background: "rgba(59,130,246,0.15)", color: "#60a5fa" }}
              >
                {activeReport.rows?.length ?? 0} rows
              </div>
            </div>

            {/* Tabs */}
            <div
              className="flex gap-1 px-6"
              style={{ borderBottom: "1px solid #334155" }}
            >
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className="px-4 py-2.5 text-sm font-medium transition-colors"
                  style={{
                    color: activeTab === tab.id ? "#3b82f6" : "#64748b",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    borderBottom: activeTab === tab.id ? "2px solid #3b82f6" : "2px solid transparent",
                    marginBottom: -1,
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto px-6 py-5">
              {activeTab === "results" && (
                <div>
                  {activeReport.datasetCompleteness && (
                    <DatasetCompleteness data={activeReport.datasetCompleteness} />
                  )}

                  {activeReport.rows && activeReport.rows.length > 0 && (
                    <ReportChart
                      rows={activeReport.rows}
                      title={activeReport.reportDefinition?.name}
                    />
                  )}

                  <DrillableReportTable
                    rows={activeReport.rows ?? []}
                    groupByFields={activeReport.reportDefinition?.group_by ?? []}
                    onRowClick={handleRowClick}
                  />

                  {activeReport.dataQualityScore && (
                    <div className="mt-4">
                      <DataQualityScore data={activeReport.dataQualityScore} />
                    </div>
                  )}
                </div>
              )}

              {activeTab === "explanation" && (
                <div className="space-y-4">
                  <div
                    className="rounded-xl p-5"
                    style={{ background: "#1e293b", border: "1px solid #334155" }}
                  >
                    <h4 className="text-sm font-semibold mb-3" style={{ color: "#94a3b8" }}>
                      AI Explanation
                    </h4>
                    <p
                      className="text-sm leading-relaxed whitespace-pre-wrap"
                      style={{ color: "#f1f5f9" }}
                    >
                      {activeReport.explanation}
                    </p>
                  </div>

                  {activeReport.anomalies && activeReport.anomalies.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold mb-3" style={{ color: "#f87171" }}>
                        Anomalies Affecting This Report
                      </h4>
                      <div className="space-y-2">
                        {activeReport.anomalies.map((a) => {
                          const s = SEVERITY_STYLE[a.severity] || SEVERITY_STYLE.low;
                          return (
                            <div
                              key={a.id}
                              className="rounded-xl px-4 py-3 flex items-start gap-3"
                              style={{
                                background: s.bg,
                                border: `1px solid ${s.border}30`,
                                borderLeft: `3px solid ${s.border}`,
                              }}
                            >
                              <AlertTriangle size={15} color={s.color} className="mt-0.5 flex-shrink-0" />
                              <div>
                                <div className="flex items-center gap-2 mb-0.5">
                                  <span className="text-xs font-semibold" style={{ color: s.color }}>
                                    {a.severity.toUpperCase()}
                                  </span>
                                  <span className="text-xs" style={{ color: "#64748b" }}>
                                    {a.category.replace(/_/g, " ")}
                                  </span>
                                  {a.invoice_number && (
                                    <span className="text-xs font-mono" style={{ color: "#60a5fa" }}>
                                      {a.invoice_number}
                                    </span>
                                  )}
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
              )}

              {activeTab === "definition" && (
                <ReportDefinitionPanel result={activeReport} />
              )}

              {activeTab === "validation" && (
                <div className="space-y-4">
                  {activeReport.validation ? (
                    <ValidationPanel validation={activeReport.validation} />
                  ) : (
                    <p className="text-sm" style={{ color: "#64748b" }}>No validation data available.</p>
                  )}

                  {activeReport.reconciliation && Object.keys(activeReport.reconciliation).length > 0 && (
                    <div
                      className="rounded-xl p-5"
                      style={{ background: "#1e293b", border: "1px solid #334155" }}
                    >
                      <h4 className="text-sm font-semibold mb-3" style={{ color: "#94a3b8" }}>
                        Reconciliation Details
                      </h4>
                      <div className="space-y-2">
                        {Object.entries(activeReport.reconciliation).map(([key, val]) => (
                          <div key={key} className="flex justify-between text-xs">
                            <span style={{ color: "#64748b" }}>{key.replace(/_/g, " ")}</span>
                            <span style={{ color: "#f1f5f9" }}>{String(val)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Drilldown Modal */}
      {drilldownRow && (
        <DrilldownModal
          runId={drilldownRow.runId}
          groupKey={drilldownRow.groupKey}
          groupLabel={drilldownRow.groupLabel}
          onClose={() => setDrilldownRow(null)}
        />
      )}
    </div>
  );
}
