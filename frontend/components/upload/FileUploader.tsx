"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Upload, X, CheckCircle, XCircle, File, Loader2 } from "lucide-react";
import { uploadInvoices, ingestFromProvider, getProviderStatus, UploadResult, SyncResult } from "@/lib/api";

type TabId = "file" | "provider";

const TABS: { id: TabId; label: string }[] = [
  { id: "file", label: "File Upload" },
  { id: "provider", label: "Peppol Provider" },
];

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileUploader() {
  const [activeTab, setActiveTab] = useState<TabId>("file");
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Provider status state
  const [providerStatus, setProviderStatus] = useState<{ connected: boolean; account?: any; error?: string } | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);

  useEffect(() => {
    if (activeTab === "provider" && providerStatus === null) {
      setStatusLoading(true);
      getProviderStatus()
        .then((s) => setProviderStatus(s))
        .catch(() => setProviderStatus({ connected: false, error: "Could not reach server" }))
        .finally(() => setStatusLoading(false));
    }
  }, [activeTab, providerStatus]);

  const addFiles = useCallback((newFiles: File[]) => {
    const xmlFiles = newFiles.filter((f) => f.name.endsWith(".xml") || f.type === "text/xml");
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      return [...prev, ...xmlFiles.filter((f) => !existing.has(f.name))];
    });
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      addFiles(Array.from(e.dataTransfer.files));
    },
    [addFiles]
  );

  const handleUpload = async () => {
    if (!files.length) return;
    setUploading(true);
    setError(null);
    setUploadResult(null);
    try {
      const r = await uploadInvoices(files);
      setUploadResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleProviderSync = async () => {
    setUploading(true);
    setError(null);
    setSyncResult(null);
    try {
      const r = await ingestFromProvider();
      setSyncResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setUploading(false);
    }
  };

  const switchTab = (tab: TabId) => {
    setActiveTab(tab);
    setUploadResult(null);
    setSyncResult(null);
    setError(null);
  };

  return (
    <div>
      {/* Tabs */}
      <div className="flex gap-1 mb-6" style={{ borderBottom: "1px solid #334155" }}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => switchTab(tab.id)}
            className="px-4 py-2.5 text-sm font-medium transition-colors relative"
            style={{
              color: activeTab === tab.id ? "#3b82f6" : "#64748b",
              background: "none",
              border: "none",
              cursor: "pointer",
              borderBottom: activeTab === tab.id ? "2px solid #3b82f6" : "2px solid transparent",
              marginBottom: -1,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div
          className="rounded-lg px-4 py-3 mb-4 text-sm"
          style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", color: "#fca5a5" }}
        >
          {error}
        </div>
      )}

      {/* File upload result banner */}
      {uploadResult && (
        <div
          className="rounded-lg px-4 py-4 mb-4"
          style={{ background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.3)" }}
        >
          <p className="text-sm font-semibold mb-2" style={{ color: "#4ade80" }}>
            Import complete
          </p>
          <div className="flex gap-6 text-sm">
            <span style={{ color: "#4ade80" }}>
              <CheckCircle size={14} className="inline mr-1" />
              {uploadResult.imported} imported
            </span>
            <span style={{ color: "#fbbf24" }}>
              {uploadResult.duplicates} duplicates
            </span>
            <span style={{ color: "#f87171" }}>
              {uploadResult.errors} errors
            </span>
          </div>
          {uploadResult.details && uploadResult.details.length > 0 && (
            <div className="mt-3 space-y-1">
              {uploadResult.details.map((d, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  {d.status === "imported" ? (
                    <CheckCircle size={13} color="#4ade80" />
                  ) : (
                    <XCircle size={13} color="#f87171" />
                  )}
                  <span style={{ color: "#94a3b8", fontFamily: "monospace" }}>{d.filename}</span>
                  {d.message && (
                    <span style={{ color: "#64748b" }}>— {d.message}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Sync result banner */}
      {syncResult && (
        <div
          className="rounded-lg px-4 py-4 mb-4"
          style={{ background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.3)" }}
        >
          <p className="text-sm font-semibold mb-3" style={{ color: "#4ade80" }}>
            Peppol sync complete
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div className="text-center rounded-lg p-3" style={{ background: "rgba(34,197,94,0.1)" }}>
              <div className="text-xl font-bold" style={{ color: "#4ade80" }}>{syncResult.synced}</div>
              <div className="text-xs mt-1" style={{ color: "#64748b" }}>Synced</div>
            </div>
            <div className="text-center rounded-lg p-3" style={{ background: "rgba(59,130,246,0.1)" }}>
              <div className="text-xl font-bold" style={{ color: "#60a5fa" }}>{syncResult.new}</div>
              <div className="text-xs mt-1" style={{ color: "#64748b" }}>New</div>
            </div>
            <div className="text-center rounded-lg p-3" style={{ background: "rgba(245,158,11,0.1)" }}>
              <div className="text-xl font-bold" style={{ color: "#fbbf24" }}>{syncResult.duplicates}</div>
              <div className="text-xs mt-1" style={{ color: "#64748b" }}>Duplicates</div>
            </div>
            <div className="text-center rounded-lg p-3" style={{ background: "rgba(239,68,68,0.1)" }}>
              <div className="text-xl font-bold" style={{ color: "#f87171" }}>{syncResult.errors}</div>
              <div className="text-xs mt-1" style={{ color: "#64748b" }}>Errors</div>
            </div>
          </div>
        </div>
      )}

      {/* Tab: File Upload */}
      {activeTab === "file" && (
        <div className="space-y-4">
          <div
            className="rounded-xl p-8 flex flex-col items-center justify-center gap-3 cursor-pointer transition-all"
            style={{
              border: dragging ? "2px dashed #3b82f6" : "2px dashed #334155",
              background: dragging ? "rgba(59,130,246,0.05)" : "transparent",
              minHeight: 200,
            }}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
          >
            <div
              className="flex items-center justify-center rounded-full"
              style={{ width: 56, height: 56, background: "rgba(59,130,246,0.1)" }}
            >
              <Upload size={24} color="#3b82f6" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium" style={{ color: "#f1f5f9" }}>
                Drop XML invoice files here or{" "}
                <span style={{ color: "#3b82f6" }}>click to browse</span>
              </p>
              <p className="text-xs mt-1" style={{ color: "#64748b" }}>
                Accepts .xml files · Multiple files supported
              </p>
            </div>
            <input
              ref={inputRef}
              type="file"
              accept=".xml,text/xml"
              multiple
              className="hidden"
              onChange={(e) => addFiles(Array.from(e.target.files || []))}
            />
          </div>

          {files.length > 0 && (
            <div className="space-y-2">
              {files.map((f, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-lg px-4 py-3"
                  style={{ background: "#1e293b", border: "1px solid #334155" }}
                >
                  <File size={16} color="#64748b" />
                  <span className="flex-1 text-sm" style={{ color: "#f1f5f9", fontFamily: "monospace" }}>
                    {f.name}
                  </span>
                  <span className="text-xs" style={{ color: "#64748b" }}>
                    {formatFileSize(f.size)}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setFiles((prev) => prev.filter((_, idx) => idx !== i));
                    }}
                    style={{ background: "none", border: "none", cursor: "pointer", padding: 2 }}
                  >
                    <X size={15} color="#64748b" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <button
            onClick={handleUpload}
            disabled={!files.length || uploading}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition-all"
            style={{
              background: files.length && !uploading ? "#3b82f6" : "#334155",
              color: files.length && !uploading ? "#fff" : "#64748b",
              border: "none",
              cursor: files.length && !uploading ? "pointer" : "not-allowed",
            }}
          >
            {uploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
            {uploading ? "Uploading…" : `Upload ${files.length} file${files.length !== 1 ? "s" : ""}`}
          </button>
        </div>
      )}

      {/* Tab: Peppol Provider */}
      {activeTab === "provider" && (
        <div className="space-y-4">
          {/* Connection Status */}
          <div
            className="rounded-xl p-5"
            style={{ background: "#1e293b", border: "1px solid #334155" }}
          >
            {statusLoading ? (
              <div className="flex items-center gap-2 text-sm" style={{ color: "#64748b" }}>
                <Loader2 size={14} className="animate-spin" />
                Checking connection…
              </div>
            ) : providerStatus ? (
              <>
                <div className="flex items-center gap-2 mb-4">
                  {providerStatus.connected ? (
                    <>
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ background: "#22c55e", boxShadow: "0 0 6px #22c55e" }}
                      />
                      <span className="text-sm font-semibold" style={{ color: "#4ade80" }}>
                        Connected ✓
                      </span>
                    </>
                  ) : (
                    <>
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ background: "#ef4444" }}
                      />
                      <span className="text-sm font-semibold" style={{ color: "#f87171" }}>
                        Not connected ✗
                      </span>
                    </>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-xs mb-1" style={{ color: "#64748b" }}>API Endpoint</p>
                    <p style={{ color: "#f1f5f9", fontFamily: "monospace", fontSize: 12 }}>
                      {providerStatus.connected ? "api-dev.e-invoice.be" : "api.e-invoice.be"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs mb-1" style={{ color: "#64748b" }}>Environment</p>
                    <p style={{ color: "#f1f5f9" }}>
                      {providerStatus.connected ? "Staging" : "Production"}
                    </p>
                  </div>
                  {providerStatus.account?.name && (
                    <div>
                      <p className="text-xs mb-1" style={{ color: "#64748b" }}>Account Name</p>
                      <p style={{ color: "#f1f5f9" }}>{providerStatus.account.name}</p>
                    </div>
                  )}
                  {providerStatus.account?.vat_id && (
                    <div>
                      <p className="text-xs mb-1" style={{ color: "#64748b" }}>VAT Number</p>
                      <p style={{ color: "#f1f5f9", fontFamily: "monospace", fontSize: 12 }}>
                        {providerStatus.account.vat_id}
                      </p>
                    </div>
                  )}
                  {providerStatus.error && (
                    <div className="col-span-2">
                      <p className="text-xs" style={{ color: "#f87171" }}>{providerStatus.error}</p>
                    </div>
                  )}
                </div>
              </>
            ) : null}
          </div>

          <p className="text-sm" style={{ color: "#64748b" }}>
            Fetch the latest invoices from your connected Peppol access point. New invoices will be
            automatically validated and anomaly-checked.
          </p>

          <button
            onClick={handleProviderSync}
            disabled={uploading}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition-all"
            style={{
              background: !uploading ? "#a855f7" : "#334155",
              color: !uploading ? "#fff" : "#64748b",
              border: "none",
              cursor: !uploading ? "pointer" : "not-allowed",
            }}
          >
            {uploading ? <Loader2 size={16} className="animate-spin" /> : null}
            {uploading ? "Syncing…" : "Sync from Peppol Inbox"}
          </button>
        </div>
      )}
    </div>
  );
}
