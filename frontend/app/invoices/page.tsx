"use client";

import { useEffect, useState, useCallback } from "react";
import { listInvoices, InvoicePage } from "@/lib/api";
import InvoiceTable from "@/components/invoices/InvoiceTable";
import { Search } from "lucide-react";

export default function InvoicesPage() {
  const [data, setData] = useState<InvoicePage | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (p: number) => {
      setLoading(true);
      setError(null);
      try {
        const res = await listInvoices(p, 20);
        setData(res);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    load(page);
  }, [page, load]);

  const filtered =
    search && data
      ? data.items.filter(
          (inv) =>
            inv.invoice_number.toLowerCase().includes(search.toLowerCase()) ||
            inv.supplier_name.toLowerCase().includes(search.toLowerCase()) ||
            inv.customer_name.toLowerCase().includes(search.toLowerCase())
        )
      : data?.items ?? [];

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-2xl font-bold"
          style={{ color: "#f1f5f9", letterSpacing: "-0.02em" }}
        >
          Invoices
        </h1>
        <p className="text-sm mt-1" style={{ color: "#64748b" }}>
          {data ? `${data.total} total invoices` : "Loading…"}
        </p>
      </div>

      {error && (
        <div
          className="rounded-lg px-4 py-3 mb-4 text-sm"
          style={{
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            color: "#fca5a5",
          }}
        >
          {error}
        </div>
      )}

      <div
        className="rounded-xl overflow-hidden"
        style={{ background: "#1e293b", border: "1px solid #334155" }}
      >
        {/* Search bar */}
        <div className="px-4 py-3" style={{ borderBottom: "1px solid #334155" }}>
          <div className="relative max-w-sm">
            <Search
              size={15}
              style={{
                position: "absolute",
                left: 12,
                top: "50%",
                transform: "translateY(-50%)",
                color: "#64748b",
              }}
            />
            <input
              type="text"
              placeholder="Search invoice #, supplier, customer…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full text-sm rounded-lg pl-9 pr-4 py-2 transition-colors focus:outline-none"
              style={{
                background: "#0f172a",
                border: "1px solid #334155",
                color: "#f1f5f9",
              }}
            />
          </div>
        </div>

        <InvoiceTable
          invoices={filtered}
          total={data?.total ?? 0}
          page={data?.page ?? 1}
          pages={data?.pages ?? 1}
          onPageChange={setPage}
          loading={loading}
        />
      </div>
    </div>
  );
}
