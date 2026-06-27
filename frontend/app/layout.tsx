import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";

export const metadata: Metadata = {
  title: "Reporto — E-Invoicing Compliance",
  description: "AI-powered e-invoicing compliance dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body style={{ background: "#0f172a", color: "#f1f5f9", margin: 0 }}>
        <div className="flex h-screen overflow-hidden" style={{ background: "#0f172a" }}>
          <Sidebar />
          <main
            className="flex-1 overflow-y-auto"
            style={{ background: "#0f172a", minHeight: "100vh" }}
          >
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
