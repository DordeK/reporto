"use client";

import { LucideIcon } from "lucide-react";

interface StatsCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  color: string;
  subtitle?: string;
  loading?: boolean;
}

export default function StatsCard({
  title,
  value,
  icon: Icon,
  color,
  subtitle,
  loading,
}: StatsCardProps) {
  if (loading) {
    return (
      <div
        className="rounded-xl p-5 animate-pulse"
        style={{ background: "#1e293b", border: "1px solid #334155" }}
      >
        <div className="h-4 rounded w-24 mb-3" style={{ background: "#334155" }} />
        <div className="h-8 rounded w-16 mb-2" style={{ background: "#334155" }} />
        <div className="h-3 rounded w-20" style={{ background: "#334155" }} />
      </div>
    );
  }

  return (
    <div
      className="rounded-xl p-5 flex flex-col gap-2 transition-all duration-200 hover:translate-y-[-2px]"
      style={{
        background: "#1e293b",
        border: "1px solid #334155",
        cursor: "default",
      }}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium" style={{ color: "#94a3b8" }}>
          {title}
        </span>
        <div
          className="flex items-center justify-center rounded-lg"
          style={{ width: 36, height: 36, background: `${color}20` }}
        >
          <Icon size={18} color={color} />
        </div>
      </div>
      <div className="text-3xl font-bold" style={{ color: "#f1f5f9", letterSpacing: "-0.02em" }}>
        {value}
      </div>
      {subtitle && (
        <div className="text-xs" style={{ color: "#64748b" }}>
          {subtitle}
        </div>
      )}
      <div
        className="h-1 rounded-full mt-1"
        style={{ background: `${color}30` }}
      >
        <div className="h-1 rounded-full w-2/3" style={{ background: color }} />
      </div>
    </div>
  );
}
