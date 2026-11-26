// Master TypeScript Data Models for Brightleaf Retail Operations Platform

export interface LiveStoreStatus {
  store_id: string;
  name: string;
  city: string;
  status: string;
  batches_processed: number;
  format: string;
}

export interface LiveStatusResponse {
  status: string;
  timestamp: string;
  total_files_ingested: number;
  quarantined_files_count: number;
  latest_ingestion: {
    file_name: string;
    store_id: string;
    records_count: number;
    imported_at: string;
  } | null;
  stores: LiveStoreStatus[];
}

export interface DashboardHeadline {
  total_sales: number;
  counter_sales: number;
  self_checkout_sales: number;
  transaction_count: number;
  average_basket: number;
  gift_card_loads: number;
}

export interface HourlySalesPoint {
  hour: number;
  sales: number;
  tx_count: number;
}

export interface TenderBreakdown {
  tender_type: string;
  total_amount: number;
  count: number;
}

export interface DepartmentBreakdown {
  dept: string;
  total_sales: number;
  item_count: number;
}

export interface WatchListEvent {
  id: string;
  store_id: string;
  seq: number;
  time: string;
  type: string;
  device_id: string;
  staff_id: string;
  amount: number;
  reason: string;
}

export interface DashboardDailyResponse {
  store_id: string;
  business_date: string;
  headline: DashboardHeadline;
  sales_by_hour: HourlySalesPoint[];
  tenders_breakdown: TenderBreakdown[];
  departments_breakdown: DepartmentBreakdown[];
  watch_list: WatchListEvent[];
}

export interface ReconciliationReport {
  id: string;
  store_id: string;
  business_date: string;
  report_type: string;
  target_id: string;
  status: 'MATCHED' | 'MISMATCH' | 'REVIEW_REQUIRED';
  net_sales_diff: number;
  tax_diff: number;
  grand_total_diff: number;
  cash_diff: number;
  comparison_details: {
    ground_truth?: {
      net_sales: number;
      tax: number;
      grand_total: number;
      departments?: Record<string, number>;
      tenders?: Record<string, number>;
    };
    stated_summary?: {
      net_sales: number;
      tax: number;
      grand_total: number;
      departments?: Record<string, number>;
      tenders?: Record<string, number>;
    };
    hub_consistency_check?: {
      is_internally_consistent: boolean;
      sum_depts_vs_net_diff: number;
      sum_tenders_vs_grand_diff: number;
    };
  };
  root_cause_analysis: string;
  created_at: string;
}

export interface ShiftReconciliationItem {
  id: string;
  shift_id: string;
  shift_no: number;
  device_id: string;
  staff_id: string;
  opening_float: number;
  closing_cash: number;
  status: 'MATCHED' | 'MISMATCH' | 'REVIEW_REQUIRED';
  cash_diff: number;
  details: {
    expected_cash: number;
    actual_cash: number;
    variance: number;
    formula?: string;
    cash_tenders?: number;
    cash_refunds?: number;
    cash_drops?: number;
  };
  root_cause_analysis: string;
}

export interface TransactionSummaryItem {
  id: string;
  store_id: string;
  seq: number;
  business_date: string;
  start_time: string;
  type: string;
  status: string;
  device_id: string;
  staff_id: string;
  shift: string;
  net_amount: number;
  tax_amount: number;
  gift_card_amount: number;
  grand_total: number;
  item_count: number;
  void_count: number;
  is_flagged: boolean;
  flag_reason: string | null;
  tenders: { tender_type: string; amount: number }[];
}

export interface TransactionListResponse {
  total: number;
  offset: number;
  limit: number;
  items: TransactionSummaryItem[];
}

export interface ReceiptLineItem {
  line_no: number;
  item_code: string;
  variant: string;
  description: string;
  dept: string;
  qty: number;
  unit_price: number;
  amount: number;
  tax_group: string;
  is_void: boolean;
}

export interface ReceiptTenderItem {
  tender_type: string;
  amount: number;
  tendered: number;
  change: number;
  card_type: string | null;
  last4: string | null;
  auth_code: string | null;
  account_id: string | null;
}

export interface ReceiptTaxItem {
  tax_group: string;
  taxable_amount: number;
  tax_amount: number;
}

export interface TransactionDetailResponse {
  id: string;
  store_id: string;
  seq: number;
  business_date: string;
  start_time: string;
  end_time: string | null;
  type: string;
  status: string;
  device_id: string;
  staff_id: string;
  shift: string;
  net_amount: number;
  tax_amount: number;
  grand_total: number;
  lines: ReceiptLineItem[];
  tenders: ReceiptTenderItem[];
  taxes: ReceiptTaxItem[];
  gift_cards: any[];
}

export interface CatalogItem {
  id: number;
  code: string;
  variant: string;
  description: string;
  dept: string;
  price: number;
  tax_group: string;
  min_age: number | null;
}

export interface CatalogResponse {
  total: number;
  items: CatalogItem[];
}

export interface BulkPreviewItem {
  code: string;
  variant: string;
  description: string;
  dept: string;
  old_price: number;
  new_price: number;
  diff: number;
  pct_change: number;
}

export interface BulkPreviewResponse {
  pct_change: number;
  dept: string | null;
  rounding_rule: string;
  items_affected: number;
  preview: BulkPreviewItem[];
}

export interface SyncStatusItem {
  file_name: string;
  status: string;
  change_id: string;
  store_id: string;
  processed_at: string;
  items: { code: string; status: string; error_code?: string; error_message?: string }[];
}

export interface CommercialStatementResponse {
  account_id: string;
  account_name: string;
  month: string;
  credit_limit: number;
  payment_terms: string;
  total_charges: number;
  total_payments: number;
  closing_balance: number;
  transactions: {
    business_date: string;
    seq: number;
    type: string;
    amount: number;
  }[];
}

export interface AIInvoiceEvaluationItem {
  invoice_no: string;
  supplier: string;
  file_name: string;
  lines_count: number;
  catalog_matches: number;
  status: string;
  discrepancy_details: string | null;
}

export interface AIInvoicesResponse {
  total_invoices: number;
  math_evaluation_pass_rate: string;
  results: AIInvoiceEvaluationItem[];
}

export interface LossPreventionIncident {
  incident_id: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  category: string;
  store_id: string;
  timestamp: string;
  device_id: string;
  staff_id: string;
  transaction_seq: number | null;
  headline: string;
  details: string;
  recommended_action: string;
}

export interface LossPreventionResponse {
  total_incidents: number;
  high_severity_count: number;
  incidents: LossPreventionIncident[];
}

export interface AIAskResponse {
  question: string;
  answer: string;
  data: any;
  confidence: number;
}

export interface QuarantineItem {
  id: number;
  file_name: string;
  store_id: string;
  file_hash: string;
  quarantine_reason: string;
  error_details: string;
  quarantined_at: string;
  payload_preview: string;
}

export interface QuarantineResponse {
  total: number;
  items: QuarantineItem[];
}

export interface PlatformMetaOptions {
  stores: { store_id: string; name: string; city: string }[];
  business_dates: string[];
  devices: string[];
  departments: { code: string; name: string }[];
  tenders: string[];
  business_accounts: { account_id: string; business_name: string; terms?: string }[];
  config: {
    project_name: string;
    version: string;
    target_margin_pct: number;
    default_variant: string;
    max_description_length: number;
    max_price_limit: number;
    default_manager_email: string;
  };
}
