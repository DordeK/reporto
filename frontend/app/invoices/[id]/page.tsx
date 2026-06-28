"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getInvoice, InvoiceDetail } from "@/lib/api";
import InvoiceDetailComponent from "@/components/invoices/InvoiceDetail";
import { Loader2 } from "lucide-react";

export default function InvoiceDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getInvoice(id)
      .then(setInvoice)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto">
      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={28} className="animate-spin" color="#3b82f6" />
        </div>
      )}
      {error && (
        <div
          className="rounded-lg px-4 py-3 text-sm"
          style={{
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            color: "#fca5a5",
          }}
        >
          Failed to load invoice: {error}
        </div>
      )}
      {!loading && !error && invoice && <InvoiceDetailComponent invoice={invoice} />}
    </div>
  );
}
