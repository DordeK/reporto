"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Upload,
  FileText,
  MessageSquare,
  AlertTriangle,
  Settings,
  Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import { listAnomalies } from "@/lib/api";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/upload", label: "Upload Invoices", icon: Upload },
  { href: "/invoices", label: "Invoices", icon: FileText },
  { href: "/reports", label: "Report Assistant", icon: MessageSquare, badge: "AI" },
  { href: "/anomalies", label: "Anomaly Center", icon: AlertTriangle, anomaly: true },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [anomalyCount, setAnomalyCount] = useState(0);

  useEffect(() => {
    listAnomalies()
      .then((data) => setAnomalyCount(data.length))
      .catch(() => setAnomalyCount(0));
  }, []);

  return (
    <aside
      className="flex flex-col flex-shrink-0"
      style={{
        width: 240,
        background: "#1e293b",
        borderRight: "1px solid #334155",
        height: "100vh",
        position: "sticky",
        top: 0,
      }}
    >
      {/* Logo */}
      <div
        className="flex items-center gap-2 px-6 py-5"
        style={{ borderBottom: "1px solid #334155" }}
      >
        <div
          className="flex items-center justify-center rounded-lg"
          style={{ width: 32, height: 32, background: "#3b82f6" }}
        >
          <Zap size={18} color="#fff" fill="#fff" />
        </div>
        <span className="font-bold text-lg" style={{ color: "#f1f5f9", letterSpacing: "-0.02em" }}>
          InvoiceAI
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));
          const showAnomalyBadge = item.anomaly && anomalyCount > 0;

          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center justify-between rounded-lg px-3 py-2.5 transition-all duration-150 group"
              style={{
                background: isActive ? "rgba(59, 130, 246, 0.15)" : "transparent",
                color: isActive ? "#3b82f6" : "#94a3b8",
                textDecoration: "none",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.05)";
                  (e.currentTarget as HTMLElement).style.color = "#f1f5f9";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.background = "transparent";
                  (e.currentTarget as HTMLElement).style.color = "#94a3b8";
                }
              }}
            >
              <div className="flex items-center gap-3">
                <Icon size={18} />
                <span className="text-sm font-medium">{item.label}</span>
              </div>
              <div className="flex items-center gap-1">
                {item.badge && (
                  <span
                    className="text-xs font-bold px-1.5 py-0.5 rounded"
                    style={{ background: "rgba(59,130,246,0.2)", color: "#3b82f6", fontSize: 10 }}
                  >
                    {item.badge}
                  </span>
                )}
                {showAnomalyBadge && (
                  <span
                    className="text-xs font-bold px-1.5 py-0.5 rounded-full"
                    style={{ background: "#ef4444", color: "#fff", fontSize: 10, minWidth: 18, textAlign: "center" }}
                  >
                    {anomalyCount}
                  </span>
                )}
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4" style={{ borderTop: "1px solid #334155" }}>
        <div className="text-xs" style={{ color: "#475569" }}>
          E-Invoicing Compliance v1.0
        </div>
        <div className="text-xs mt-0.5" style={{ color: "#334155" }}>
          Hackathon Demo
        </div>
      </div>
    </aside>
  );
}
