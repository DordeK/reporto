'use client';

interface Check {
  name: string;
  icon: string;
  passed: number;
  failed: number;
  ok: boolean;
  warning: string | null;
}

interface Props {
  data: {
    score: number;
    total_invoices: number;
    checks: Check[];
    warnings: string[];
  };
}

export default function DataQualityScore({ data }: Props) {
  const scoreColor = data.score >= 95 ? 'text-green-400' : data.score >= 80 ? 'text-amber-400' : 'text-red-400';

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <span>🛡</span> Data Quality Score
        </h4>
        <span className={`text-2xl font-bold ${scoreColor}`}>{data.score}%</span>
      </div>
      <div className="space-y-1">
        {data.checks.map((check, i) => (
          <div key={i} className="flex items-center justify-between text-xs">
            <span className={check.ok ? 'text-green-400' : 'text-amber-400'}>
              {check.ok ? '✓' : '⚠'} {check.name}
            </span>
            {!check.ok && check.warning && (
              <span className="text-amber-400/70">{check.warning}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
