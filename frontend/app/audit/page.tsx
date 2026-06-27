'use client';
import { useEffect, useState } from 'react';
import { listAuditLogs } from '@/lib/api';

export default function AuditPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    setLoading(true);
    listAuditLogs({ page, limit: 50, action: filter || undefined }).then(r => {
      setLogs(r.items);
      setTotal(r.total);
      setLoading(false);
    });
  }, [page, filter]);

  const actionBadge = (action: string) => {
    const colors: Record<string, string> = {
      'report.generate': 'bg-blue-900 text-blue-300',
      'invoice.upload': 'bg-green-900 text-green-300',
      'invoice.sync_peppol': 'bg-purple-900 text-purple-300',
    };
    return colors[action] || 'bg-slate-700 text-slate-300';
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Audit Log</h1>
          <p className="text-slate-400 text-sm mt-1">Complete record of who generated what, when, and with which query</p>
        </div>
        <div className="text-slate-400 text-sm">{total} entries</div>
      </div>

      {/* Filter */}
      <div className="flex gap-2 mb-4">
        {['', 'report.generate', 'invoice.upload', 'invoice.sync_peppol'].map(a => (
          <button
            key={a}
            onClick={() => { setFilter(a); setPage(1); }}
            className={`px-3 py-1 rounded text-xs ${filter === a ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
          >
            {a || 'All'}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-slate-400 text-xs">
              <th className="text-left p-3">Timestamp</th>
              <th className="text-left p-3">Action</th>
              <th className="text-left p-3">Actor</th>
              <th className="text-left p-3">IP Address</th>
              <th className="text-left p-3">Details</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="p-6 text-center text-slate-500">Loading…</td></tr>
            ) : logs.map(log => (
              <tr key={log.id} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                <td className="p-3 text-slate-400 font-mono text-xs whitespace-nowrap">
                  {new Date(log.created_at).toLocaleString('en-BE')}
                </td>
                <td className="p-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-mono ${actionBadge(log.action)}`}>
                    {log.action}
                  </span>
                </td>
                <td className="p-3 text-slate-300">{log.actor || '—'}</td>
                <td className="p-3 text-slate-400 font-mono text-xs">{log.ip_address || '—'}</td>
                <td className="p-3 text-slate-400 text-xs">
                  {log.details ? (
                    <details>
                      <summary className="cursor-pointer text-slate-300">View</summary>
                      <pre className="mt-1 text-xs bg-slate-900 p-2 rounded overflow-auto max-w-xs">
                        {JSON.stringify(log.details, null, 2)}
                      </pre>
                    </details>
                  ) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex justify-between items-center mt-4">
        <button
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1}
          className="px-3 py-1 bg-slate-700 text-slate-300 rounded text-sm disabled:opacity-40"
        >
          Previous
        </button>
        <span className="text-slate-400 text-sm">Page {page}</span>
        <button
          onClick={() => setPage(p => p + 1)}
          disabled={logs.length < 50}
          className="px-3 py-1 bg-slate-700 text-slate-300 rounded text-sm disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}
