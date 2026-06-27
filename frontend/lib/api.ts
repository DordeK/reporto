const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface DashboardStats {
  totalInvoices: number;
  receivedInvoices: number;
  sentInvoices: number;
  totalVat: number;
  totalSpend: number;
  anomalyCount: number;
  highSeverityAnomalies: number;
  vatByRate: { tax_percent: number; tax_amount: number }[];
  invoicesBySource: { upload?: number; email?: number; provider?: number; peppol?: number };
  recentReports: { id: string; user_prompt: string; report_name: string; row_count: number; created_at: string }[];
}

export interface UploadResult {
  imported: number;
  duplicates: number;
  errors: number;
  details?: { filename: string; status: "imported" | "duplicate" | "error"; message?: string }[];
}

export interface Invoice {
  id: string;
  invoice_number: string;
  supplier_name: string;
  customer_name: string;
  issue_date: string;
  payable_amount: number;
  tax_amount: number;
  currency: string;
  source: "upload" | "email" | "provider" | "peppol";
  anomaly_count: number;
  direction?: "received" | "sent";
  invoice_type?: string;
}

export interface InvoicePage {
  items: Invoice[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface TaxSubtotal {
  tax_category: string;
  tax_rate: number;
  taxable_amount: number;
  tax_amount: number;
}

export interface InvoiceLine {
  line_number: number;
  description: string;
  quantity: number;
  unit_price: number;
  line_amount: number;
  vat_rate: number;
  unit?: string;
}

export interface Anomaly {
  id: string;
  invoice_id: string;
  invoice_number?: string;
  severity: "high" | "medium" | "low";
  category: string;
  message: string;
  detected_at: string;
}

export interface InvoiceDetail extends Invoice {
  supplier_vat_id?: string;
  supplier_country?: string;
  supplier_iban?: string;
  supplier_address?: string;
  customer_vat_id?: string;
  customer_country?: string;
  customer_iban?: string;
  customer_address?: string;
  due_date?: string;
  payment_terms?: string;
  note?: string;
  tax_subtotals: TaxSubtotal[];
  lines: InvoiceLine[];
  anomalies: Anomaly[];
}

export interface ReportDefinition {
  name: string;
  description?: string;
  dimensions?: string[];
  metrics?: string[];
  filters?: Record<string, unknown>;
  group_by?: string[];
  order_by?: string[];
}

export interface DatasetCompleteness {
  total_invoices: number;
  matched_invoices: number | null;
  excluded_invoices: number | null;
  exclusion_reasons: string[];
  completeness_note: string;
}

export interface DataQualityCheck {
  name: string;
  icon: string;
  passed: number;
  failed: number;
  ok: boolean;
  warning: string | null;
}

export interface DataQualityScore {
  score: number;
  total_invoices: number;
  checks: DataQualityCheck[];
  warnings: string[];
}

export interface ValidationResult {
  errors: Array<{ step: number; code: string; message: string }>;
  warnings: string[];
  passed: boolean;
}

export interface ReportResult {
  reportDefinition: ReportDefinition;
  sql: string;
  rows: Record<string, unknown>[];
  explanation: string;
  reportRunId?: string;
  anomalies?: Anomaly[];
  validation?: ValidationResult;
  datasetCompleteness?: DatasetCompleteness;
  reconciliation?: Record<string, any>;
  dataQualityScore?: DataQualityScore;
}

export interface ReportRun {
  id: string;
  prompt: string;
  created_at: string;
  row_count?: number;
  report_name?: string;
}

// ─── API Functions ────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return apiFetch<DashboardStats>("/dashboard/stats");
}

export async function uploadInvoices(files: File[]): Promise<UploadResult> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const res = await fetch(`${BASE_URL}/invoices/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`Upload failed ${res.status}: ${text}`);
  }
  return res.json() as Promise<UploadResult>;
}

export interface SyncResult {
  synced: number;
  new: number;
  duplicates: number;
  errors: number;
}

export async function ingestFromProvider(): Promise<SyncResult> {
  return apiFetch<SyncResult>("/invoices/ingest-provider", { method: "POST" });
}

export async function getProviderStatus(): Promise<{ connected: boolean; account?: any; error?: string }> {
  const r = await fetch(`${BASE_URL}/invoices/provider/status`);
  return r.json();
}

export async function generateReportEnhanced(prompt: string): Promise<ReportResult> {
  const r = await fetch(`${BASE_URL}/reports/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function reportDrilldown(runId: string, groupKey?: Record<string, any>): Promise<{
  invoices: Array<{
    id: string; invoice_number: string; issue_date: string;
    payable_amount: number; tax_amount: number; currency: string;
    supplier_name: string; supplier_vat_id: string; customer_name: string;
  }>;
  count: number;
}> {
  const params = groupKey ? `?group_key=${encodeURIComponent(JSON.stringify(groupKey))}` : "";
  const r = await fetch(`${BASE_URL}/reports/${runId}/drilldown${params}`);
  return r.json();
}

export async function generateBelgianVatReturn(body: {
  period_start: string; period_end: string;
  declarant_vat: string; declarant_name: string;
  declarant_street: string; declarant_city: string;
  declarant_postal: string; declarant_email: string;
}): Promise<{
  period_start: string; period_end: string;
  grids: any; xml: string; format: string; warnings: string[];
}> {
  const r = await fetch(`${BASE_URL}/reports/belgian-vat-return`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

export async function listAuditLogs(params?: { action?: string; actor?: string; page?: number; limit?: number }): Promise<{
  total: number; page: number; limit: number;
  items: Array<{
    id: string; action: string; entity_type: string; entity_id: string;
    actor: string; ip_address: string; details: any; created_at: string;
  }>;
}> {
  const qs = new URLSearchParams(params as any).toString();
  const r = await fetch(`${BASE_URL}/audit-logs/${qs ? "?" + qs : ""}`);
  return r.json();
}

export async function listInvoices(page: number, limit: number): Promise<InvoicePage> {
  return apiFetch<InvoicePage>(`/invoices?page=${page}&limit=${limit}`);
}

export async function getInvoice(id: string): Promise<InvoiceDetail> {
  return apiFetch<InvoiceDetail>(`/invoices/${id}`);
}

export async function generateReport(prompt: string): Promise<ReportResult> {
  const r = await fetch(`${BASE_URL}/reports/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function listReports(): Promise<ReportRun[]> {
  return apiFetch<ReportRun[]>("/reports");
}

export interface ReportRunDetail {
  id: string;
  user_prompt: string;
  report_definition: Record<string, unknown>;
  generated_sql: string | null;
  result: { rows: Record<string, unknown>[]; row_count: number } | null;
  explanation: string | null;
  created_at: string;
}

export async function getReportRun(id: string): Promise<ReportRunDetail> {
  return apiFetch<ReportRunDetail>(`/reports/${id}`);
}

export interface SlovenianVatResult {
  period_start: string;
  period_end: string;
  entry_count: number;
  boxes: Record<string, string>;
  kpr_xml: string;
  ddvo_xml: string;
  format: string;
  kpr_schema: string;
  ddvo_schema: string;
  warnings: string[];
}

export async function generateSlovenianVatReturn(params: {
  period_start: string;
  period_end: string;
  tax_number: string;
  taxpayer_name: string;
}): Promise<SlovenianVatResult> {
  const r = await fetch(`${BASE_URL}/reports/slovenian-vat-return`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function listAnomalies(severity?: string): Promise<Anomaly[]> {
  const qs = severity ? `?severity=${severity}` : "";
  const res = await apiFetch<{ items: Anomaly[] } | Anomaly[]>(`/anomalies${qs}`);
  return Array.isArray(res) ? res : res.items ?? [];
}

export interface OutgoingLine {
  description: string;
  quantity: number;
  unit_price: number;
  tax_percent: number;
  tax_category: string;
  unit_code?: string;
}

export interface OutgoingParty {
  name: string;
  vat_id: string;
  street_name?: string;
  city_name?: string;
  postal_zone?: string;
  country_code: string;
  endpoint_id?: string;
  endpoint_scheme?: string;
  iban?: string;
  contact_email?: string;
  contact_telephone?: string;
  contact_name?: string;
}

export interface SendInvoicePayload {
  invoice_number: string;
  issue_date: string;
  due_date?: string;
  currency: string;
  note?: string;
  payment_terms_note?: string;
  buyer_reference?: string;
  supplier: OutgoingParty;
  customer: OutgoingParty;
  lines: OutgoingLine[];
  send_via_peppol: boolean;
}

export interface SendInvoiceResult {
  invoice_id: string;
  status: string;
  ubl_xml: string;
  peppol: Record<string, unknown> | null;
  peppol_error: string | null;
}

export async function sendInvoice(payload: SendInvoicePayload): Promise<SendInvoiceResult> {
  const r = await fetch(`${BASE_URL}/invoices/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "Unknown error");
    throw new Error(`Send failed ${r.status}: ${text}`);
  }
  return r.json();
}
