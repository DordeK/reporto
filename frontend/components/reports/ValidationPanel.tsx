'use client';

interface Props {
  validation: {
    errors: Array<{ step: number; code: string; message: string }>;
    warnings: string[];
    passed: boolean;
  };
}

export default function ValidationPanel({ validation }: Props) {
  if (validation.passed && validation.warnings.length === 0) {
    return (
      <div className="flex items-center gap-2 text-green-400 text-sm mb-4">
        <span>✓</span> All validation checks passed
      </div>
    );
  }
  return (
    <div className="bg-slate-800 border border-amber-600/50 rounded-lg p-4 mb-4">
      <h4 className="text-sm font-semibold text-amber-400 mb-2">Validation Issues</h4>
      {validation.errors.map((err, i) => (
        <div key={i} className="text-xs text-red-400 mb-1">
          Step {err.step} [{err.code}]: {err.message}
        </div>
      ))}
      {validation.warnings.map((w, i) => (
        <div key={i} className="text-xs text-amber-400 mb-1">⚠ {w}</div>
      ))}
    </div>
  );
}
