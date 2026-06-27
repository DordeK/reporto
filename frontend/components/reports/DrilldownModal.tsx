'use client';
import { useEffect, useState } from 'react';
import { reportDrilldown } from '@/lib/api';

interface Invoice {
  id: string;
  invoice_number: string;
  issue_date: string;
  payable_amount: number;
  tax_amount: number;
  currency: string;
  supplier_name: string;
  customer_name: string;
}

interface Props {
  runId: string;
  groupKey?: Record<string, any>;
  groupLabel?: string;
  onClose: () => void;
}

export default function DrilldownModal({ runId, groupKey, groupLabel, onClose }: Props) {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    reportDrilldown(runId, groupKey).then(r => {
      setInvoices(r.invoices);
      setLoading(false);
    });
  }, [runId, groupKey]);

  const fmt = (n: number | null) => n != null
    ? new Intl.NumberFormat('en-BE', { style: 'currency', currency: 'EUR' }).format(n)
    : '—';

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-3xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <h3 className="font-semibold text-slate-100">
            Drill-down{groupLabel ? `: ${groupLabel}` : ''}
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-100 text-xl">✕</button>
        </div>
        <div className="overflow-auto flex-1 p-4">
          {loading ? (
            <div className="text-slate-400 text-sm">Loading invoices…</div>
          ) : invoices.length === 0 ? (
            <div className="text-slate-400 text-sm">No invoices found.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-400 border-b border-slate-700">
                  <th className="pb-2 pr-4">Invoice #</th>
                  <th className="pb-2 pr-4">Supplier</th>
                  <th className="pb-2 pr-4">Date</th>
                  <th className="pb-2 pr-4 text-right">Total</th>
                  <th className="pb-2 text-right">VAT</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map(inv => (
                  <tr key={inv.id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                    <td className="py-2 pr-4 font-mono text-xs text-blue-400">{inv.invoice_number}</td>
                    <td className="py-2 pr-4 text-slate-300">{inv.supplier_name}</td>
                    <td className="py-2 pr-4 text-slate-400">
                      {inv.issue_date ? new Date(inv.issue_date).toLocaleDateString('en-BE') : '—'}
                    </td>
                    <td className="py-2 pr-4 text-right text-slate-100">{fmt(inv.payable_amount)}</td>
                    <td className="py-2 text-right text-amber-400">{fmt(inv.tax_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        <div className="p-4 border-t border-slate-700 text-xs text-slate-400">
          {!loading && `${invoices.length} invoice(s) contributing to this result`}
        </div>
      </div>
    </div>
  );
}
