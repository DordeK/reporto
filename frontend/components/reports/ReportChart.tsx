"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

const COLORS = ["#3b82f6", "#22c55e", "#a855f7", "#f59e0b", "#ef4444", "#06b6d4", "#f97316"];

interface ReportChartProps {
  rows: Record<string, unknown>[];
  title?: string;
}

function detectChartData(rows: Record<string, unknown>[]): {
  type: "bar" | "pie" | "none";
  labelKey: string;
  valueKey: string;
} {
  if (!rows || rows.length === 0) return { type: "none", labelKey: "", valueKey: "" };

  const cols = Object.keys(rows[0]);
  const numericCols = cols.filter((c) => rows.some((r) => typeof r[c] === "number"));
  const textCols = cols.filter((c) => !numericCols.includes(c));

  if (numericCols.length === 0) return { type: "none", labelKey: "", valueKey: "" };

  const labelKey = textCols[0] || cols[0];
  const valueKey = numericCols[0];

  if (rows.length <= 8) {
    return { type: "pie", labelKey, valueKey };
  }
  return { type: "bar", labelKey, valueKey };
}

export default function ReportChart({ rows, title }: ReportChartProps) {
  const { type, labelKey, valueKey } = detectChartData(rows);

  if (type === "none") return null;

  const data = rows.map((r) => ({
    name: String(r[labelKey] ?? "").slice(0, 30),
    value: Number(r[valueKey] ?? 0),
  }));

  const formatValue = (v: number) => {
    if (Math.abs(v) > 10000)
      return new Intl.NumberFormat("en-EU", {
        style: "currency",
        currency: "EUR",
        maximumFractionDigits: 0,
      }).format(v);
    return v.toLocaleString("en-EU", { maximumFractionDigits: 2 });
  };

  return (
    <div
      className="rounded-xl p-4 mb-4"
      style={{ background: "#0f172a", border: "1px solid #334155" }}
    >
      {title && (
        <h4 className="text-sm font-semibold mb-3" style={{ color: "#f1f5f9" }}>
          {title}
        </h4>
      )}

      {type === "bar" && (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) =>
                Math.abs(v) > 1000 ? `€${(v / 1000).toFixed(0)}k` : String(v)
              }
            />
            <Tooltip
              contentStyle={{
                background: "#1e293b",
                border: "1px solid #334155",
                borderRadius: 8,
                color: "#f1f5f9",
                fontSize: 12,
              }}
              formatter={(value: number) => [formatValue(value), valueKey.replace(/_/g, " ")]}
            />
            <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]}>
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}

      {type === "pie" && (
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={3}
              dataKey="value"
            >
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "#1e293b",
                border: "1px solid #334155",
                borderRadius: 8,
                color: "#f1f5f9",
                fontSize: 12,
              }}
              formatter={(value: number) => [formatValue(value), valueKey.replace(/_/g, " ")]}
            />
            <Legend
              formatter={(v) => (
                <span style={{ color: "#94a3b8", fontSize: 11 }}>{v}</span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
