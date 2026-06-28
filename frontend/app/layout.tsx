import type { Metadata } from "next";
import "./globals.css";
import AppShell from "@/components/layout/AppShell";

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
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body style={{ background: "#0f172a", color: "#f1f5f9", margin: 0 }}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
