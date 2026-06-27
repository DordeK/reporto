"use client";

import { useState, useCallback } from "react";
import { generateReport, ReportResult } from "@/lib/api";
import ReportChat, { ChatMessage } from "@/components/reports/ReportChat";
import ReportChart from "@/components/reports/ReportChart";
import ReportDefinitionPanel from "@/components/reports/ReportDefinitionPanel";
import DatasetCompleteness from "@/components/reports/DatasetCompleteness";
import DataQualityScore from "@/components/reports/DataQualityScore";
import ValidationPanel from "@/components/reports/ValidationPanel";
import DrilldownModal from "@/components/reports/DrilldownModal";
import DrillableReportTable from "@/components/reports/DrillableReportTable";
import { AlertTriangle, Sparkles, Download } from "lucide-react";

type ReportTab = "results" | "explanation" | "definition" | "validation";

let msgCounter = 0;
const newId = () => `msg-${++msgCounter}-${Date.now()}`;

const SEVERITY_STYLE: Record<string, { bg: string; color: string; border: string }> = {
  high: { bg: "rgba(239,68,68,0.1)", color: "#f87171", border: "#ef4444" },
  medium: { bg: "rgba(245,158,11,0.1)", color: "#fbbf24", border: "#f59e0b" },
  low: { bg: "rgba(59,130,246,0.1)", color: "#60a5fa", border: "#3b82f6" },
};

export default function ReportsPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeReport, setActiveReport] = useState<ReportResult | null>(null);
  const [activeTab, setActiveTab] = useState<ReportTab>("results");
  const [drilldownRow, setDrilldownRow] = useState<{
    runId: string;
    groupKey: Record<string, any>;
    groupLabel: string;
  } | null>(null);

  const handleSubmit = useCallback(async (prompt: string) => {
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
    } catch (e: unknown) {
      const errMsg = e instanceof Error ? e.message : "Report generation failed";

      // Check if the backend signalled a non-report input
      let notAReportMessage: string | null = null;
      try {
        const parsed = JSON.parse(errMsg.replace(/^API error \d+:\s*/, ""));
        if (parsed?.detail?.type === "not_a_report") {
          notAReportMessage = parsed.detail.message;
        }
      } catch {
        // not JSON — fall through to normal error
      }

      if (notAReportMessage) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === aiMsgId
              ? { ...m, content: notAReportMessage as string, loading: false }
              : m
          )
        );
      } else {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === aiMsgId
              ? { ...m, content: "", loading: false, error: errMsg }
              : m
          )
        );
      }
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
            }}
            loading={loading}
          />
        </div>
      </div>

      {/* Right Panel: Report Display (60%) */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {!activeReport ? (
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
