export default function SettingsPage() {
  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-2xl font-bold"
          style={{ color: "#f1f5f9", letterSpacing: "-0.02em" }}
        >
          Settings
        </h1>
        <p className="text-sm mt-1" style={{ color: "#64748b" }}>
          System configuration and preferences
        </p>
      </div>

      <div
        className="rounded-xl p-5 mb-4"
        style={{ background: "#1e293b", border: "1px solid #334155" }}
      >
        <h2 className="text-sm font-semibold mb-4" style={{ color: "#f1f5f9" }}>
          API Configuration
        </h2>
        <div className="space-y-4">
          {[
            { label: "Backend API URL", value: "http://localhost:8000", type: "text" },
            { label: "AI Model", value: "gpt-4o", type: "text" },
            { label: "Default Currency", value: "EUR", type: "text" },
          ].map((field) => (
            <div key={field.label}>
              <label className="block text-xs font-medium mb-1" style={{ color: "#64748b" }}>
                {field.label}
              </label>
              <input
                type={field.type}
                defaultValue={field.value}
                className="w-full text-sm rounded-lg px-3 py-2 focus:outline-none"
                style={{
                  background: "#0f172a",
                  border: "1px solid #334155",
                  color: "#f1f5f9",
                }}
              />
            </div>
          ))}
        </div>
      </div>

      <div
        className="rounded-xl p-5"
        style={{ background: "#1e293b", border: "1px solid #334155" }}
      >
        <h2 className="text-sm font-semibold mb-4" style={{ color: "#f1f5f9" }}>
          Compliance Rules
        </h2>
        <div className="space-y-3">
          {[
            "Check for missing VAT IDs",
            "Flag duplicate invoice numbers",
            "Validate tax rate consistency",
            "Alert on large invoice amounts",
            "Cross-reference supplier IBAN",
          ].map((rule) => (
            <div key={rule} className="flex items-center justify-between">
              <span className="text-sm" style={{ color: "#94a3b8" }}>
                {rule}
              </span>
              <div
                className="rounded-full flex items-center"
                style={{
                  width: 38,
                  height: 22,
                  background: "rgba(59,130,246,0.3)",
                  padding: "2px",
                  cursor: "pointer",
                }}
              >
                <div
                  className="rounded-full"
                  style={{ width: 18, height: 18, background: "#3b82f6", marginLeft: "auto" }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
