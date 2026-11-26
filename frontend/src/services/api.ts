// Centralized API Service for Brightleaf Retail Operations Platform
import type {
  LiveStatusResponse,
  DashboardDailyResponse,
  ReconciliationReport,
  ShiftReconciliationItem,
  TransactionListResponse,
  TransactionDetailResponse,
  CatalogResponse,
  BulkPreviewResponse,
  SyncStatusItem,
  CommercialStatementResponse,
  AIInvoicesResponse,
  LossPreventionResponse,
  AIAskResponse,
  QuarantineResponse,
} from '../types';

const BASE_URL = '/api/v1';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  // Live Telemetry
  getLiveStatus: () => request<LiveStatusResponse>('/live/status'),

  // Dashboard Overview
  getDashboardDaily: (date: string, storeId?: string) => {
    const params = new URLSearchParams({ date });
    if (storeId && storeId !== 'ALL') {
      params.append('store_id', storeId);
    }
    return request<DashboardDailyResponse>(`/dashboard/daily?${params.toString()}`);
  },

  // Reconciliation
  getEodReconciliation: (storeId: string, date: string) => {
    return request<ReconciliationReport>(`/reconciliation/daily?store_id=${storeId}&date=${date}`);
  },
  getShiftReconciliation: (storeId: string, date: string) => {
    return request<ShiftReconciliationItem[]>(`/reconciliation/shifts?store_id=${storeId}&date=${date}`);
  },

  // Transactions
  getTransactions: (filters: {
    store_id?: string;
    date?: string;
    dept?: string;
    tender_type?: string;
    type?: string;
    device_id?: string;
    staff_id?: string;
    has_voids?: boolean;
    limit?: number;
    offset?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters.store_id && filters.store_id !== 'ALL') params.append('store_id', filters.store_id);
    if (filters.date) params.append('date', filters.date);
    if (filters.dept) params.append('dept', filters.dept);
    if (filters.tender_type) params.append('tender_type', filters.tender_type);
    if (filters.type) params.append('type', filters.type);
    if (filters.device_id) params.append('device_id', filters.device_id);
    if (filters.staff_id) params.append('staff_id', filters.staff_id);
    if (filters.has_voids) params.append('has_voids', 'true');
    params.append('limit', String(filters.limit || 50));
    params.append('offset', String(filters.offset || 0));
    return request<TransactionListResponse>(`/transactions?${params.toString()}`);
  },
  getTransactionDetail: (txId: string) => {
    return request<TransactionDetailResponse>(`/transactions/${txId}`);
  },

  // Pricing & Hub Sync
  getCatalogItems: (dept?: string, search?: string, limit = 100, offset = 0) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (dept) params.append('dept', dept);
    if (search) params.append('search', search);
    return request<CatalogResponse>(`/pricing/items?${params.toString()}`);
  },
  previewBulkPrice: (payload: { pct_change: number; dept?: string | null; rounding_rule: string }) => {
    return request<BulkPreviewResponse>('/pricing/preview-bulk', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
  applyAndPublishPrices: (items: any[], publishToStores: string[] = ['BL01', 'BL02']) => {
    return request<{ status: string; items_updated: number; published_stores: string[] }>('/pricing/apply-and-publish', {
      method: 'POST',
      body: JSON.stringify({ items, publish_to_stores: publishToStores }),
    });
  },
  getSyncStatus: () => request<SyncStatusItem[]>('/pricing/sync-status'),
  getCommercialStatement: (accountId: string, month = '2026-10') => {
    return request<CommercialStatementResponse>(`/pricing/commercial-statement?account_id=${accountId}&month=${month}`);
  },

  // AI Multimodal & Intelligence
  getAIInvoices: () => request<AIInvoicesResponse>('/ai/invoices'),
  getInvoiceDetail: (filename: string) => request<any>(`/ai/invoices/${filename}`),
  publishInvoicePricing: (filename: string, storeIds: string[] = ['BL01', 'BL02']) => {
    return request<{ status: string; change_files: string[] }>(`/ai/invoices/${filename}/publish-pricing`, {
      method: 'POST',
      body: JSON.stringify({ store_ids: storeIds }),
    });
  },
  getLossPrevention: (date: string, storeId?: string) => {
    const params = new URLSearchParams({ date });
    if (storeId && storeId !== 'ALL') params.append('store_id', storeId);
    return request<LossPreventionResponse>(`/ai/loss-prevention?${params.toString()}`);
  },
  askStoreAI: (question: string, storeId?: string, date = '2026-10-04') => {
    return request<AIAskResponse>('/ai/ask', {
      method: 'POST',
      body: JSON.stringify({
        question,
        store_id: storeId && storeId !== 'ALL' ? storeId : null,
        date,
      }),
    });
  },

  // Quarantine & Hub Health
  getQuarantine: () => request<QuarantineResponse>('/quarantine'),
  getQuarantinePayload: (fileId: number) => request<{ file_name: string; payload: string }>(`/quarantine/${fileId}`),
};
