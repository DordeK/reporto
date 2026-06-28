'use client';
import { useEffect, useState } from 'react';
import { listAuditLogs, getReportRun, ReportRunDetail } from '@/lib/api';

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('en-BE', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'number') {
    return v > 999 || v < -999
      ? new Intl.NumberFormat('en-EU', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 }).format(v)
      : v.toLocaleString('en-EU', { maximumFractionDigits: 4 });
  }
  if (typeof v === 'string' && /^\d{4}-\d{2}-\d{2}/.test(v)) {
    try { return new Date(v).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }); }
    catch { return v; }
  }
  return String(v);
}

function DataTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows || rows.length === 0)
    return <p className="text-xs" style={{ color: '#64748b' }}>No rows returned.</p>;
  const cols = Object.keys(rows[0]);
  return (
    <div className="rounded-lg overflow-hidden" style={{ border: '1px solid #334155' }}>
      <div className="overflow-x-auto">
        <table className="w-full text-xs" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#0f172a' }}>
              {cols.map(c => (
                <th key={c} className="px-3 py-2 text-left font-semibold uppercase tracking-wider"
                  style={{ color: '#64748b', whiteSpace: 'nowrap' }}>
                  {c.replace(/_/g, ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} style={{ borderTop: '1px solid #1e293b' }}>
                {cols.map(c => (
                  <td key={c} className="px-3 py-2"
                    style={{
                      color: typeof row[c] === 'number' ? '#f1f5f9' : '#94a3b8',
                      fontFamily: typeof row[c] === 'number' ? 'monospace' : 'inherit',
                      whiteSpace: 'nowrap',
                    }}>
                    {formatValue(row[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="px-3 py-1.5 text-xs" style={{ background: '#0f172a', borderTop: '1px solid #334155', color: '#475569' }}>
        {rows.length} row{rows.length !== 1 ? 's' : ''}
      </div>
    </div>
  );
}

function ReportDetail({ entityId }: { entityId: string }) {
  const [detail, setDetail] = useState<ReportRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getReportRun(entityId)
      .then(setDetail)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [entityId]);

  if (loading) return <p className="text-xs py-3" style={{ color: '#64748b' }}>Loading…</p>;
  if (error) return <p className="text-xs py-3" style={{ color: '#f87171' }}>{error}</p>;
  if (!detail) return null;

  const rows = detail.result?.rows ?? [];

  return (
    <div className="space-y-4 py-4 px-2">
      {/* Question */}
      <div>
        <div className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: '#64748b' }}>Question</div>
        <p className="text-sm" style={{ color: '#f1f5f9' }}>{detail.user_prompt}</p>
      </div>

      {/* SQL */}
      {detail.generated_sql && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: '#64748b' }}>SQL Executed</div>
          <pre className="text-xs rounded-lg p-3 overflow-x-auto"
            style={{ background: '#0f172a', border: '1px solid #334155', color: '#7dd3fc', fontFamily: 'monospace' }}>
            {detail.generated_sql}
          </pre>
        </div>
      )}

      {/* Explanation */}
      {detail.explanation && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: '#64748b' }}>AI Explanation</div>
          <p className="text-sm leading-relaxed" style={{ color: '#94a3b8' }}>{detail.explanation}</p>
        </div>
      )}

      {/* Returned data */}
      <div>
        <div className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: '#64748b' }}>
          Returned Data ({rows.length} row{rows.length !== 1 ? 's' : ''})
        </div>
        <DataTable rows={rows} />
      </div>
    </div>
  );
}

export default function AuditPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    listAuditLogs({ page, limit: 50, action: 'report.generate' }).then(r => {
      setLogs(r.items);
      setTotal(r.total);
      setLoading(false);
    });
  }, [page]);

  const toggle = (id: string) => setExpanded(prev => prev === id ? null : id);

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold" style={{ color: '#f1f5f9' }}>Report History</h1>
          <p className="text-sm mt-0.5" style={{ color: '#64748b' }}>Every report generated — question, SQL, and returned data</p>
        </div>
        <div className="text-sm" style={{ color: '#64748b' }}>{total} report{total !== 1 ? 's' : ''}</div>
      </div>

      <div className="rounded-xl overflow-hidden" style={{ border: '1px solid #334155' }}>
        {loading ? (
          <div className="p-8 text-center text-sm" style={{ color: '#64748b' }}>Loading…</div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-sm" style={{ color: '#64748b' }}>No reports generated yet.</div>
        ) : (
          <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#0f172a', borderBottom: '1px solid #334155' }}>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: '#64748b' }}>When</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: '#64748b' }}>Question</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: '#64748b' }}>Report</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider" style={{ color: '#64748b' }}>Rows</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: '#64748b' }}>Actor</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log, i) => (
                <>
                  <tr
                    key={log.id}
                    onClick={() => toggle(log.id)}
                    style={{
                      borderTop: i > 0 ? '1px solid #1e293b' : 'none',
                      background: expanded === log.id ? 'rgba(59,130,246,0.06)' : 'transparent',
                      cursor: 'pointer',
                    }}
                    onMouseEnter={e => { if (expanded !== log.id) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.02)'; }}
                    onMouseLeave={e => { if (expanded !== log.id) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                  >
                    <td className="px-4 py-3 font-mono text-xs whitespace-nowrap" style={{ color: '#64748b' }}>
                      {formatDate(log.created_at)}
                    </td>
                    <td className="px-4 py-3 max-w-xs" style={{ color: '#f1f5f9' }}>
                      <span className="line-clamp-1">{log.details?.prompt ?? '—'}</span>
                    </td>
                    <td className="px-4 py-3 text-xs" style={{ color: '#94a3b8' }}>
                      {log.details?.report_name ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs" style={{ color: '#94a3b8' }}>
                      {log.details?.row_count ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-xs" style={{ color: '#64748b' }}>
                      {log.actor ?? '—'}
                    </td>
                  </tr>

                  {expanded === log.id && log.entity_id && (
                    <tr key={`${log.id}-detail`} style={{ borderTop: '1px solid #1e293b', background: 'rgba(59,130,246,0.04)' }}>
                      <td colSpan={5} className="px-6" style={{ borderBottom: '2px solid rgba(59,130,246,0.3)' }}>
                        <ReportDetail entityId={log.entity_id} />
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="flex justify-between items-center mt-4">
        <button
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1}
          className="px-3 py-1.5 rounded-lg text-sm"
          style={{ background: '#1e293b', color: '#94a3b8', border: '1px solid #334155', cursor: page === 1 ? 'not-allowed' : 'pointer', opacity: page === 1 ? 0.4 : 1 }}
        >
          Previous
        </button>
        <span className="text-sm" style={{ color: '#64748b' }}>Page {page}</span>
        <button
          onClick={() => setPage(p => p + 1)}
          disabled={logs.length < 50}
          className="px-3 py-1.5 rounded-lg text-sm"
          style={{ background: '#1e293b', color: '#94a3b8', border: '1px solid #334155', cursor: logs.length < 50 ? 'not-allowed' : 'pointer', opacity: logs.length < 50 ? 0.4 : 1 }}
        >
          Next
        </button>
      </div>
    </div>
  );
}
