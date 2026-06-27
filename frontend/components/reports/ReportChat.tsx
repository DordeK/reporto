"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Sparkles, User, Bot, Loader2 } from "lucide-react";
import { ReportResult } from "@/lib/api";


export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  result?: ReportResult;
  loading?: boolean;
  error?: string;
}

interface ReportChatProps {
  messages: ChatMessage[];
  onSubmit: (prompt: string) => void;
  onSelectReport: (result: ReportResult) => void;
  loading: boolean;
}

export default function ReportChat({ messages, onSubmit, onSelectReport, loading }: ReportChatProps) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    onSubmit(text);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Chat History */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full py-10 text-center">
            <div
              className="flex items-center justify-center rounded-2xl mb-4"
              style={{ width: 56, height: 56, background: "rgba(168,85,247,0.15)" }}
            >
              <Sparkles size={26} color="#a855f7" />
            </div>
            <h3 className="text-base font-semibold mb-1" style={{ color: "#f1f5f9" }}>
              AI Report Assistant
            </h3>
            <p className="text-sm max-w-xs" style={{ color: "#64748b" }}>
              Ask me to analyze your invoice data, generate VAT reports, or identify compliance
              issues.
            </p>
          </div>
        )}


        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
          >
            {/* Avatar */}
            <div
              className="flex items-center justify-center rounded-full flex-shrink-0"
              style={{
                width: 30,
                height: 30,
                background: msg.role === "user" ? "rgba(59,130,246,0.2)" : "rgba(168,85,247,0.2)",
                marginTop: 4,
              }}
            >
              {msg.role === "user" ? (
                <User size={14} color="#60a5fa" />
              ) : (
                <Bot size={14} color="#c084fc" />
              )}
            </div>

            {/* Bubble */}
            <div
              className={`flex flex-col max-w-[85%] ${msg.role === "user" ? "items-end" : "items-start"}`}
            >
              <div
                className="rounded-xl px-4 py-3 text-sm"
                style={{
                  background: msg.role === "user"
                    ? "rgba(59,130,246,0.15)"
                    : "#1e293b",
                  border: "1px solid",
                  borderColor: msg.role === "user" ? "rgba(59,130,246,0.3)" : "#334155",
                  color: "#f1f5f9",
                  lineHeight: 1.6,
                }}
              >
                {msg.loading ? (
                  <div className="flex items-center gap-2" style={{ color: "#64748b" }}>
                    <Loader2 size={14} className="animate-spin" />
                    <span className="text-sm">Analyzing your data…</span>
                    <span className="animate-pulse">●</span>
                    <span className="animate-pulse" style={{ animationDelay: "0.2s" }}>●</span>
                    <span className="animate-pulse" style={{ animationDelay: "0.4s" }}>●</span>
                  </div>
                ) : msg.error ? (
                  <span style={{ color: "#f87171" }}>{msg.error}</span>
                ) : (
                  <span>{msg.content}</span>
                )}
              </div>

              {/* View Report button */}
              {msg.result && !msg.loading && (
                <button
                  onClick={() => onSelectReport(msg.result!)}
                  className="mt-1.5 text-xs font-medium px-3 py-1 rounded-lg transition-colors"
                  style={{
                    background: "rgba(168,85,247,0.15)",
                    border: "1px solid rgba(168,85,247,0.3)",
                    color: "#c084fc",
                    cursor: "pointer",
                  }}
                >
                  View full report →
                </button>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>


      {/* Input */}
      <div
        className="px-4 py-3 flex gap-2"
        style={{ borderTop: "1px solid #334155" }}
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          placeholder="Ask about your invoices…"
          rows={1}
          disabled={loading}
          className="flex-1 text-sm rounded-xl px-4 py-2.5 resize-none focus:outline-none transition-colors"
          style={{
            background: "#0f172a",
            border: "1px solid #334155",
            color: "#f1f5f9",
            lineHeight: 1.5,
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={!input.trim() || loading}
          className="flex items-center justify-center rounded-xl transition-all"
          style={{
            width: 42,
            height: 42,
            background: input.trim() && !loading ? "#3b82f6" : "#334155",
            border: "none",
            cursor: input.trim() && !loading ? "pointer" : "not-allowed",
            flexShrink: 0,
          }}
        >
          {loading ? (
            <Loader2 size={16} color="#64748b" className="animate-spin" />
          ) : (
            <Send size={16} color={input.trim() ? "#fff" : "#64748b"} />
          )}
        </button>
      </div>
    </div>
  );
}
