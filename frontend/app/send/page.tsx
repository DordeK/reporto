"use client";

import { useState } from "react";
import { Plus, Trash2, Send, CheckCircle, AlertCircle, FileCode, ChevronDown, ChevronUp } from "lucide-react";
import {
  sendInvoice,
  SendInvoicePayload,
  OutgoingLine,
  OutgoingParty,
  SendInvoiceResult,
} from "@/lib/api";

const card: React.CSSProperties = {
  background: "#1e293b",
  border: "1px solid #334155",
  borderRadius: 12,
  padding: 24,
};

const label: React.CSSProperties = {
  display: "block",
  fontSize: 12,
  fontWeight: 600,
  color: "#94a3b8",
  marginBottom: 6,
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const input: React.CSSProperties = {
  width: "100%",
  background: "#0f172a",
  border: "1px solid #334155",
  borderRadius: 8,
  padding: "8px 12px",
  color: "#f1f5f9",
  fontSize: 14,
  outline: "none",
  boxSizing: "border-box",
};

const sectionTitle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 700,
  color: "#64748b",
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  marginBottom: 16,
  paddingBottom: 8,
  borderBottom: "1px solid #1e293b",
};

const EU_COUNTRIES = [
  ["BE", "Belgium"], ["BG", "Bulgaria"], ["CZ", "Czechia"], ["DK", "Denmark"],
  ["DE", "Germany"], ["EE", "Estonia"], ["IE", "Ireland"], ["GR", "Greece"],
  ["ES", "Spain"], ["FR", "France"], ["HR", "Croatia"], ["IT", "Italy"],
  ["CY", "Cyprus"], ["LV", "Latvia"], ["LT", "Lithuania"], ["LU", "Luxembourg"],
  ["HU", "Hungary"], ["MT", "Malta"], ["NL", "Netherlands"], ["AT", "Austria"],
  ["PL", "Poland"], ["PT", "Portugal"], ["RO", "Romania"], ["SI", "Slovenia"],
  ["SK", "Slovakia"], ["FI", "Finland"], ["SE", "Sweden"],
  ["GB", "United Kingdom"], ["CH", "Switzerland"], ["NO", "Norway"],
  ["RS", "Serbia"], ["US", "United States"],
];

const EU_VAT_RATES = [0, 6, 9, 12, 21];
const TAX_CATEGORIES = [
  { value: "S", label: "S — Standard" },
  { value: "Z", label: "Z — Zero rated" },
  { value: "E", label: "E — Exempt" },
  { value: "AE", label: "AE — Reverse charge" },
  { value: "K", label: "K — Intra-EU" },
];

const emptyParty = (country = "BE"): OutgoingParty => ({
  name: "",
  vat_id: "",
  street_name: "",
  city_name: "",
  postal_zone: "",
  country_code: country,
  endpoint_id: "",
  iban: "",
  contact_email: "",
});

const emptyLine = (): OutgoingLine => ({
  description: "",
  quantity: 1,
  unit_price: 0,
  tax_percent: 21,
  tax_category: "S",
});

function Field({
  label: lbl,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string | number;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <div>
      <label style={label}>{lbl}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={input}
      />
    </div>
  );
}

function PartyForm({
  title,
  party,
  onChange,
  showIban = false,
}: {
  title: string;
  party: OutgoingParty;
  onChange: (p: OutgoingParty) => void;
  showIban?: boolean;
}) {
  const set = (k: keyof OutgoingParty) => (v: string) => onChange({ ...party, [k]: v });
  return (
    <div>
      <p style={sectionTitle}>{title}</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Field label="Company name" value={party.name} onChange={set("name")} placeholder="Acme NV" />
        <Field label="VAT number" value={party.vat_id} onChange={set("vat_id")} placeholder="BE0123456789" />
        <Field label="Street" value={party.street_name || ""} onChange={set("street_name")} placeholder="Rue de la Loi 16" />
        <Field label="City" value={party.city_name || ""} onChange={set("city_name")} placeholder="Brussels" />
        <Field label="Postal code" value={party.postal_zone || ""} onChange={set("postal_zone")} placeholder="1000" />
        <div>
          <label style={label}>Country</label>
          <select style={{ ...input, cursor: "pointer" }} value={party.country_code} onChange={(e) => set("country_code")(e.target.value)}>
            {EU_COUNTRIES.map(([code, name]) => (
              <option key={code} value={code}>{code} — {name}</option>
            ))}
          </select>
        </div>
        <Field
          label="Peppol endpoint ID"
          value={party.endpoint_id || ""}
          onChange={set("endpoint_id")}
          placeholder="0208:0123456789"
        />
        {showIban && (
          <Field label="IBAN" value={party.iban || ""} onChange={set("iban")} placeholder="BE68539007547034" />
        )}
        <Field label="Contact email" value={party.contact_email || ""} onChange={set("contact_email")} placeholder="billing@company.be" />
      </div>
    </div>
  );
}

function LineRow({
  line,
  index,
  onChange,
  onRemove,
}: {
  line: OutgoingLine;
  index: number;
  onChange: (l: OutgoingLine) => void;
  onRemove: () => void;
}) {
  const lineTotal = (line.quantity * line.unit_price).toFixed(2);
  const vatAmount = (line.quantity * line.unit_price * line.tax_percent / 100).toFixed(2);

  return (
    <div
      className="grid gap-2 items-end"
      style={{
        gridTemplateColumns: "2fr 80px 100px 100px 120px 80px 32px",
        background: "#0f172a",
        borderRadius: 8,
        padding: "10px 12px",
        border: "1px solid #1e293b",
      }}
    >
      <div>
        {index === 0 && <label style={{ ...label, marginBottom: 4 }}>Description</label>}
        <input
          style={input}
          value={line.description}
          onChange={(e) => onChange({ ...line, description: e.target.value })}
          placeholder="Description"
        />
      </div>
      <div>
        {index === 0 && <label style={{ ...label, marginBottom: 4 }}>Qty</label>}
        <input
          type="number"
          style={input}
          value={line.quantity}
          min={0}
          step="any"
          onChange={(e) => onChange({ ...line, quantity: parseFloat(e.target.value) || 0 })}
        />
      </div>
      <div>
        {index === 0 && <label style={{ ...label, marginBottom: 4 }}>Unit price</label>}
        <input
          type="number"
          style={input}
          value={line.unit_price}
          min={0}
          step="any"
          onChange={(e) => onChange({ ...line, unit_price: parseFloat(e.target.value) || 0 })}
        />
      </div>
      <div>
        {index === 0 && <label style={{ ...label, marginBottom: 4 }}>VAT %</label>}
        <select
          style={{ ...input, cursor: "pointer" }}
          value={line.tax_percent}
          onChange={(e) => onChange({ ...line, tax_percent: parseFloat(e.target.value) })}
        >
          {EU_VAT_RATES.map((r) => (
            <option key={r} value={r}>{r}%</option>
          ))}
        </select>
      </div>
      <div>
        {index === 0 && <label style={{ ...label, marginBottom: 4 }}>Category</label>}
        <select
          style={{ ...input, cursor: "pointer" }}
          value={line.tax_category}
          onChange={(e) => onChange({ ...line, tax_category: e.target.value })}
        >
          {TAX_CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>{c.value}</option>
          ))}
        </select>
      </div>
      <div>
        {index === 0 && <label style={{ ...label, marginBottom: 4 }}>Subtotal</label>}
        <div style={{ ...input, color: "#94a3b8", userSelect: "none" }}>
          {lineTotal}
        </div>
      </div>
      <div style={{ display: "flex", alignItems: index === 0 ? "flex-end" : "center", paddingBottom: index === 0 ? 0 : 0 }}>
        <button
          onClick={onRemove}
          style={{ background: "none", border: "none", cursor: "pointer", color: "#475569", padding: 4 }}
        >
          <Trash2 size={16} />
        </button>
      </div>
    </div>
  );
}

function TotalsBar({ lines }: { lines: OutgoingLine[] }) {
  const subtotal = lines.reduce((s, l) => s + l.quantity * l.unit_price, 0);
  const vat = lines.reduce((s, l) => s + l.quantity * l.unit_price * l.tax_percent / 100, 0);
  const total = subtotal + vat;

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "flex-end",
        gap: 32,
        padding: "12px 16px",
        background: "#0f172a",
        borderRadius: 8,
        border: "1px solid #1e293b",
      }}
    >
      {[
        ["Subtotal (excl. VAT)", subtotal],
        ["VAT", vat],
        ["Total payable", total],
      ].map(([lbl, val]) => (
        <div key={lbl as string} style={{ textAlign: "right" }}>
          <div style={{ fontSize: 11, color: "#475569", marginBottom: 2 }}>{lbl}</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: lbl === "Total payable" ? "#3b82f6" : "#f1f5f9" }}>
            €{(val as number).toFixed(2)}
          </div>
        </div>
      ))}
    </div>
  );
}

function XmlPreview({ xml }: { xml: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ ...card, marginTop: 0 }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          background: "none",
          border: "none",
          cursor: "pointer",
          color: "#64748b",
          fontSize: 13,
          fontWeight: 600,
          padding: 0,
        }}
      >
        <FileCode size={16} />
        Generated UBL XML
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      {open && (
        <pre
          style={{
            marginTop: 12,
            background: "#0f172a",
            border: "1px solid #1e293b",
            borderRadius: 8,
            padding: 16,
            fontSize: 11,
            color: "#94a3b8",
            overflowX: "auto",
            maxHeight: 400,
            overflowY: "auto",
          }}
        >
          {xml}
        </pre>
      )}
    </div>
  );
}

export default function SendInvoicePage() {
  const today = new Date().toISOString().slice(0, 10);
  const in30 = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);

  const [invoiceNumber, setInvoiceNumber] = useState(`INV-${Date.now().toString().slice(-6)}`);
  const [issueDate, setIssueDate] = useState(today);
  const [dueDate, setDueDate] = useState(in30);
  const [currency, setCurrency] = useState("EUR");
  const [note, setNote] = useState("");
  const [paymentTerms, setPaymentTerms] = useState("Payment within 30 days");
  const [buyerRef, setBuyerRef] = useState("");
  const [sendViaPeppol, setSendViaPeppol] = useState(true);

  const [supplier, setSupplier] = useState<OutgoingParty>(emptyParty("SI"));
  const [customer, setCustomer] = useState<OutgoingParty>(emptyParty("BE"));
  const [lines, setLines] = useState<OutgoingLine[]>([emptyLine()]);

  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<SendInvoiceResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const updateLine = (i: number) => (l: OutgoingLine) =>
    setLines((ls) => ls.map((x, idx) => (idx === i ? l : x)));

  const removeLine = (i: number) =>
    setLines((ls) => ls.filter((_, idx) => idx !== i));

  const submit = async () => {
    setError(null);
    setResult(null);
    setSubmitting(true);
    try {
      const payload: SendInvoicePayload = {
        invoice_number: invoiceNumber,
        issue_date: issueDate,
        due_date: dueDate || undefined,
        currency,
        note: note || undefined,
        payment_terms_note: paymentTerms || undefined,
        buyer_reference: buyerRef || undefined,
        supplier,
        customer,
        lines,
        send_via_peppol: sendViaPeppol,
      };
      const res = await sendInvoice(payload);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return (
      <div className="p-4 md:p-6 max-w-4xl mx-auto flex flex-col gap-4">
        <div style={{ ...card, borderColor: "rgba(34,197,94,0.4)", background: "rgba(34,197,94,0.05)" }}>
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle size={24} color="#22c55e" />
            <div>
              <h2 style={{ color: "#f1f5f9", fontWeight: 700, fontSize: 18 }}>Invoice sent successfully</h2>
              <p style={{ color: "#64748b", fontSize: 13 }}>Invoice ID: {result.invoice_id}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4" style={{ marginTop: 12 }}>
            <div style={{ background: "#0f172a", borderRadius: 8, padding: 12, border: "1px solid #1e293b" }}>
              <div style={{ fontSize: 11, color: "#475569", marginBottom: 4 }}>Storage</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#22c55e" }}>Saved to DB</div>
            </div>
            <div style={{ background: "#0f172a", borderRadius: 8, padding: 12, border: "1px solid #1e293b" }}>
              <div style={{ fontSize: 11, color: "#475569", marginBottom: 4 }}>Peppol status</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: result.peppol ? "#22c55e" : result.peppol_error ? "#f59e0b" : "#475569" }}>
                {result.peppol
                  ? `Sent — ${(result.peppol as Record<string, string>).state ?? "accepted"}`
                  : result.peppol_error
                  ? "Not sent (see below)"
                  : "Skipped"}
              </div>
            </div>
            <div style={{ background: "#0f172a", borderRadius: 8, padding: 12, border: "1px solid #1e293b" }}>
              <div style={{ fontSize: 11, color: "#475569", marginBottom: 4 }}>Peppol ID</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#f1f5f9" }}>
                {(result.peppol as Record<string, string> | null)?.id ?? "—"}
              </div>
            </div>
          </div>

          {result.peppol_error && (
            <div style={{ marginTop: 12, background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.3)", borderRadius: 8, padding: 12 }}>
              <p style={{ fontSize: 12, color: "#f59e0b", fontWeight: 600 }}>Peppol delivery note</p>
              <p style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>{result.peppol_error}</p>
              <p style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
                The invoice was saved locally. Check the error above and re-send with corrected details.
              </p>
            </div>
          )}
        </div>

        <XmlPreview xml={result.ubl_xml} />

        <div className="flex gap-3">
          <button
            onClick={() => { setResult(null); setLines([emptyLine()]); setSupplier(emptyParty()); setCustomer(emptyParty()); }}
            style={{ background: "#3b82f6", color: "#fff", border: "none", borderRadius: 8, padding: "10px 20px", cursor: "pointer", fontWeight: 600, fontSize: 14 }}
          >
            Send another invoice
          </button>
          <a
            href="/invoices"
            style={{ background: "#1e293b", color: "#94a3b8", border: "1px solid #334155", borderRadius: 8, padding: "10px 20px", cursor: "pointer", fontWeight: 600, fontSize: 14, textDecoration: "none", display: "inline-flex", alignItems: "center" }}
          >
            View all invoices
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto flex flex-col gap-4">
      <div className="mb-2">
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "#f1f5f9", letterSpacing: "-0.02em" }}>
          Send Invoice via Peppol
        </h1>
        <p style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>
          Compose a UBL 2.1 invoice, deliver it over the Peppol network, and store it automatically.
        </p>
      </div>

      {error && (
        <div style={{ ...card, borderColor: "rgba(239,68,68,0.4)", background: "rgba(239,68,68,0.05)" }}>
          <div className="flex items-center gap-2">
            <AlertCircle size={16} color="#ef4444" />
            <p style={{ color: "#fca5a5", fontSize: 13 }}>{error}</p>
          </div>
        </div>
      )}

      {/* Header fields */}
      <div style={card}>
        <p style={sectionTitle}>Invoice details</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Field label="Invoice number" value={invoiceNumber} onChange={setInvoiceNumber} placeholder="INV-001" />
          <Field label="Issue date" value={issueDate} onChange={setIssueDate} type="date" />
          <Field label="Due date" value={dueDate} onChange={setDueDate} type="date" />
          <div>
            <label style={label}>Currency</label>
            <select style={{ ...input, cursor: "pointer" }} value={currency} onChange={(e) => setCurrency(e.target.value)}>
              {["EUR", "USD", "GBP", "CHF"].map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
          <Field label="Note (optional)" value={note} onChange={setNote} placeholder="Free text note on invoice" />
          <Field label="Payment terms" value={paymentTerms} onChange={setPaymentTerms} placeholder="Payment within 30 days" />
        </div>
        <div className="mt-3">
          <Field label="Buyer reference (optional)" value={buyerRef} onChange={setBuyerRef} placeholder="PO-2024-001" />
        </div>
      </div>

      {/* Parties */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div style={card}>
          <PartyForm title="Supplier (you)" party={supplier} onChange={setSupplier} showIban />
        </div>
        <div style={card}>
          <PartyForm title="Customer (recipient)" party={customer} onChange={setCustomer} />
        </div>
      </div>

      {/* Lines */}
      <div style={card}>
        <p style={sectionTitle}>Invoice lines</p>
        <div className="flex flex-col gap-2">
          {lines.map((ln, i) => (
            <LineRow
              key={i}
              index={i}
              line={ln}
              onChange={updateLine(i)}
              onRemove={() => removeLine(i)}
            />
          ))}
        </div>
        <button
          onClick={() => setLines((ls) => [...ls, emptyLine()])}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            marginTop: 12,
            background: "none",
            border: "1px dashed #334155",
            borderRadius: 8,
            padding: "8px 14px",
            color: "#64748b",
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          <Plus size={14} /> Add line
        </button>
        <div style={{ marginTop: 16 }}>
          <TotalsBar lines={lines} />
        </div>
      </div>

      {/* Send options */}
      <div style={card}>
        <p style={sectionTitle}>Delivery</p>
        <label style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={sendViaPeppol}
            onChange={(e) => setSendViaPeppol(e.target.checked)}
            style={{ width: 16, height: 16, cursor: "pointer" }}
          />
          <div>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#f1f5f9" }}>Send via Peppol (e-invoice.be)</span>
            <p style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
              Delivers the UBL XML to the customer's Peppol endpoint. Requires a valid EINVOICE_BE_API_KEY.
            </p>
          </div>
        </label>
      </div>

      {/* Submit */}
      <div className="flex justify-end">
        <button
          onClick={submit}
          disabled={submitting || lines.length === 0}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            background: submitting ? "#1e3a5f" : "#3b82f6",
            color: "#fff",
            border: "none",
            borderRadius: 10,
            padding: "12px 28px",
            fontSize: 15,
            fontWeight: 700,
            cursor: submitting ? "not-allowed" : "pointer",
            opacity: submitting ? 0.7 : 1,
            transition: "opacity 0.15s",
          }}
        >
          <Send size={17} />
          {submitting ? "Sending…" : "Send Invoice"}
        </button>
      </div>
    </div>
  );
}
