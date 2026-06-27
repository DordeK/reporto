"use client";

interface ReportTableProps {
  rows: Record<string, unknown>[];
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") {
    if (v > 1000 || v < -1000) {
      return new Intl.NumberFormat("en-EU", {
        style: "currency",
        currency: "EUR",
        maximumFractionDigits: 2,
      }).format(v);
    }
    return v.toLocaleString("en-EU", { maximumFractionDigits: 4 });
  }
  if (typeof v === "string") {
    // Try to detect dates
    if (/^\d{4}-\d{2}-\d{2}/.test(v)) {
      try {
        return new Date(v).toLocaleDateString("en-GB", {
          day: "numeric",
          month: "short",
          year: "numeric",
        });
      } catch {
        return v;
      }
    }
    return v;
  }
  return String(v);
}

function isNumericColumn(rows: Record<string, unknown>[], col: string): boolean {
  return rows.some((r) => typeof r[col] === "number");
}

export default function ReportTable({ rows }: ReportTableProps) {
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

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{ border: "1px solid #334155" }}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#0f172a", borderBottom: "1px solid #334155" }}>
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider"
                  style={{
                    color: "#64748b",
                    textAlign: isNumericColumn(rows, col) ? "right" : "left",
                  }}
                >
                  {col.replace(/_/g, " ")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={i}
                style={{
                  borderBottom: i < rows.length - 1 ? "1px solid #1e293b" : "none",
                  background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.01)",
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div
        className="px-4 py-2 text-xs"
        style={{ background: "#0f172a", borderTop: "1px solid #334155", color: "#475569" }}
      >
        {rows.length} row{rows.length !== 1 ? "s" : ""}
      </div>
    </div>
  );
}
