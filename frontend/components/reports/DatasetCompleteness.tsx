'use client';

interface Props {
  data: {
    total_invoices: number;
    matched_invoices: number | null;
    excluded_invoices: number | null;
    exclusion_reasons: string[];
    completeness_note: string;
  };
}

export default function DatasetCompleteness({ data }: Props) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 mb-4">
      <h4 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
        <span>📊</span> Dataset Completeness
      </h4>
      <div className="grid grid-cols-3 gap-4 mb-3">
        <div className="text-center">
          <div className="text-xl font-bold text-slate-100">{data.total_invoices.toLocaleString()}</div>
          <div className="text-xs text-slate-400">Total in DB</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-blue-400">{data.matched_invoices?.toLocaleString() ?? '—'}</div>
          <div className="text-xs text-slate-400">Matching Filters</div>
        </div>
        <div className="text-center">
          <div className="text-xl font-bold text-slate-400">{data.excluded_invoices?.toLocaleString() ?? '—'}</div>
          <div className="text-xs text-slate-400">Excluded</div>
        </div>
      </div>
      {data.exclusion_reasons.length > 0 && (
        <div className="text-xs text-slate-400 bg-slate-900 rounded p-2">
          <span className="text-slate-300">Reason: </span>
          {data.exclusion_reasons.join('; ')}
        </div>
      )}
    </div>
  );
}
