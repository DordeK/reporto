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

interface VatByRate {
  rate: number;
  taxable_amount: number;
  vat_amount: number;
}

interface BySource {
  upload: number;
  email: number;
  provider: number;
}

const COLORS = ["#3b82f6", "#22c55e", "#a855f7", "#f59e0b", "#ef4444"];

const formatEur = (v: number) =>
  new Intl.NumberFormat("en-EU", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(v);

interface VatChartProps {
  vatByRate: VatByRate[];
  loading?: boolean;
}

export function VatBarChart({ vatByRate, loading }: VatChartProps) {
  if (loading) {
    return (
      <div
        className="rounded-xl p-5 h-64 animate-pulse"
        style={{ background: "#1e293b", border: "1px solid #334155" }}
      >
        <div className="h-4 w-32 rounded mb-4" style={{ background: "#334155" }} />
        <div className="h-full rounded" style={{ background: "#334155", opacity: 0.3 }} />
      </div>
    );
  }

  const data = vatByRate.map((r) => ({
    name: `${r.rate}%`,
    "VAT Amount": r.vat_amount,
    "Taxable Amount": r.taxable_amount,
  }));

  return (
    <div
      className="rounded-xl p-5"
      style={{ background: "#1e293b", border: "1px solid #334155" }}
    >
      <h3 className="text-sm font-semibold mb-4" style={{ color: "#f1f5f9" }}>
        VAT by Rate
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `€${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, color: "#f1f5f9" }}
            formatter={(value: number) => [formatEur(value), ""]}
          />
          <Bar dataKey="VAT Amount" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Taxable Amount" fill="#1d4ed8" radius={[4, 4, 0, 0]} opacity={0.5} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

interface SourceChartProps {
  bySource: BySource;
  loading?: boolean;
}

const SOURCE_COLORS: Record<string, string> = {
  Upload: "#3b82f6",
  Email: "#22c55e",
  Provider: "#a855f7",
};

export function SourcePieChart({ bySource, loading }: SourceChartProps) {
  if (loading) {
    return (
      <div
        className="rounded-xl p-5 h-64 animate-pulse"
        style={{ background: "#1e293b", border: "1px solid #334155" }}
      >
        <div className="h-4 w-32 rounded mb-4" style={{ background: "#334155" }} />
        <div className="h-full rounded-full mx-auto w-40" style={{ background: "#334155", opacity: 0.3 }} />
      </div>
    );
  }

  const data = [
    { name: "Upload", value: bySource.upload },
    { name: "Email", value: bySource.email },
    { name: "Provider", value: bySource.provider },
  ].filter((d) => d.value > 0);

  return (
    <div
      className="rounded-xl p-5"
      style={{ background: "#1e293b", border: "1px solid #334155" }}
    >
      <h3 className="text-sm font-semibold mb-4" style={{ color: "#f1f5f9" }}>
        Invoices by Source
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={80}
            paddingAngle={3}
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={SOURCE_COLORS[entry.name] || COLORS[index % COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8, color: "#f1f5f9" }}
          />
          <Legend
            formatter={(value) => <span style={{ color: "#94a3b8", fontSize: 12 }}>{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
