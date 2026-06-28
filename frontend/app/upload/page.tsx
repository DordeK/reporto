import FileUploader from "@/components/upload/FileUploader";

export default function UploadPage() {
  return (
    <div className="p-4 md:p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1
          className="text-2xl font-bold"
          style={{ color: "#f1f5f9", letterSpacing: "-0.02em" }}
        >
          Import Invoices
        </h1>
        <p className="text-sm mt-1" style={{ color: "#64748b" }}>
          Upload XML invoices or sync from your Peppol provider
        </p>
      </div>

      <div
        className="rounded-xl p-6"
        style={{ background: "#1e293b", border: "1px solid #334155" }}
      >
        <FileUploader />
      </div>
    </div>
  );
}
