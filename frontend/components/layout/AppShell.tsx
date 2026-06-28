"use client";

import { useState } from "react";
import Sidebar from "./Sidebar";
import { Menu } from "lucide-react";
import { Zap } from "lucide-react";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "#0f172a" }}>
      {/* Mobile header bar */}
      <div
        className="md:hidden fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-4"
        style={{
          height: 56,
          background: "#1e293b",
          borderBottom: "1px solid #334155",
        }}
      >
        <button
          onClick={() => setSidebarOpen(true)}
          className="flex items-center justify-center rounded-lg"
          style={{
            width: 36,
            height: 36,
            background: "rgba(255,255,255,0.05)",
            border: "1px solid #334155",
            cursor: "pointer",
          }}
        >
          <Menu size={18} color="#94a3b8" />
        </button>
        <div className="flex items-center gap-2">
          <div
            className="flex items-center justify-center rounded-lg"
            style={{ width: 28, height: 28, background: "#3b82f6" }}
          >
            <Zap size={15} color="#fff" fill="#fff" />
          </div>
          <span className="font-bold text-sm" style={{ color: "#f1f5f9", letterSpacing: "-0.02em" }}>
            Reporto
          </span>
        </div>
        <div style={{ width: 36 }} />
      </div>

      {/* Sidebar overlay on mobile */}
      {sidebarOpen && (
        <div
          className="md:hidden fixed inset-0 z-40"
          style={{ background: "rgba(0,0,0,0.6)" }}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div
        className={`fixed md:relative z-50 md:z-auto transition-transform duration-200 md:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        style={{ height: "100vh" }}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main content */}
      <main
        className="flex-1 overflow-y-auto"
        style={{
          background: "#0f172a",
          minHeight: "100vh",
          paddingTop: 0,
        }}
      >
        {/* Spacer for mobile header */}
        <div className="md:hidden" style={{ height: 56 }} />
        {children}
      </main>
    </div>
  );
}
