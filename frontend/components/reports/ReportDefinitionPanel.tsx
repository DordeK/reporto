"use client";

import { ReportResult } from "@/lib/api";
import { useState } from "react";
import { Copy, Check } from "lucide-react";

interface ReportDefinitionPanelProps {
  result: ReportResult;
}

function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl overflow-hidden" style={{ border: "1px solid #334155" }}>
      <div
        className="flex items-center justify-between px-4 py-2"
        style={{ background: "#0f172a", borderBottom: "1px solid #334155" }}
      >
        <span className="text-xs font-medium uppercase tracking-wider" style={{ color: "#64748b" }}>
          {language}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-xs px-2 py-1 rounded transition-colors"
          style={{
            background: "rgba(255,255,255,0.05)",
            border: "1px solid #334155",
            color: "#64748b",
            cursor: "pointer",
          }}
        >
          {copied ? (
            <>
              <Check size={11} color="#4ade80" />
              <span style={{ color: "#4ade80" }}>Copied</span>
            </>
          ) : (
            <>
              <Copy size={11} />
              Copy
            </>
          )}
        </button>
      </div>
      <pre
        className="overflow-x-auto text-xs p-4"
        style={{
          background: "#060d1a",
          color: "#94a3b8",
          margin: 0,
          lineHeight: 1.7,
          fontFamily: '"JetBrains Mono", "Fira Code", Consolas, monospace',
        }}
      >
        {code}
      </pre>
    </div>
  );
}

export default function ReportDefinitionPanel({ result }: ReportDefinitionPanelProps) {
  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-semibold mb-2" style={{ color: "#94a3b8" }}>
          Report Definition (JSON)
        </h4>
        <CodeBlock
          code={JSON.stringify(result.reportDefinition, null, 2)}
          language="JSON"
        />
      </div>
      <div>
        <h4 className="text-sm font-semibold mb-2" style={{ color: "#94a3b8" }}>
          Generated SQL Query
        </h4>
        <CodeBlock code={result.sql} language="SQL" />
      </div>
    </div>
  );
}
