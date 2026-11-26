import React, { useEffect, useState } from 'react';
import {
  Search,
  Filter,
  Send,
  CheckCircle2,
  AlertOctagon,
  RefreshCw,
  Sliders,
  Building,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import type {
  CatalogItem,
  BulkPreviewItem,
  SyncStatusItem,
  CommercialStatementResponse,
} from '../types';
import { Badge } from '../components/common/Badge';

export const PriceBookView: React.FC = () => {
  const { meta } = useApp();
  const [activeTab, setActiveTab] = useState<'catalog' | 'sync' | 'commercial'>('catalog');

  // Catalog State
  const [catalogItems, setCatalogItems] = useState<CatalogItem[]>([]);
  const [, setTotalCatalog] = useState<number>(0);
  const [search, setSearch] = useState<string>('');
  const [dept, setDept] = useState<string>('');
  const [catalogLoading, setCatalogLoading] = useState<boolean>(true);

  // Bulk Adjustment Drawer State
  const [showBulkDrawer, setShowBulkDrawer] = useState<boolean>(false);
  const [pctChange, setPctChange] = useState<number>(5.0);
  const [bulkDept, setBulkDept] = useState<string>('20');
  const [roundingRule, setRoundingRule] = useState<string>('ROUND_UP_9');
  const [previewItems, setPreviewItems] = useState<BulkPreviewItem[]>([]);
  const [previewLoading, setPreviewLoading] = useState<boolean>(false);
  const [publishSuccess, setPublishSuccess] = useState<string | null>(null);

  // Hub Sync State
  const [syncHistory, setSyncHistory] = useState<SyncStatusItem[]>([]);
  const [syncLoading, setSyncLoading] = useState<boolean>(false);

  // Commercial Statement State
  const [selectedAccount, setSelectedAccount] = useState<string>('BA-0001');
  const [statement, setStatement] = useState<CommercialStatementResponse | null>(null);
  const [statementLoading, setStatementLoading] = useState<boolean>(false);

  // Load Catalog
  const fetchCatalog = () => {
    setCatalogLoading(true);
    api
      .getCatalogItems(dept || undefined, search || undefined, 100, 0)
      .then((res) => {
        setCatalogItems(res.items);
        setTotalCatalog(res.total);
        setCatalogLoading(false);
      })
      .catch(() => setCatalogLoading(false));
  };

  useEffect(() => {
    if (activeTab === 'catalog') {
      fetchCatalog();
    } else if (activeTab === 'sync') {
      fetchSyncStatus();
    } else if (activeTab === 'commercial') {
      fetchStatement();
    }
  }, [activeTab, dept, search, selectedAccount]);

  const fetchSyncStatus = () => {
    setSyncLoading(true);
    api
      .getSyncStatus()
      .then((res) => {
        setSyncHistory(res);
        setSyncLoading(false);
      })
      .catch(() => setSyncLoading(false));
  };

  const fetchStatement = () => {
    setStatementLoading(true);
    api
      .getCommercialStatement(selectedAccount)
      .then((res) => {
        setStatement(res);
        setStatementLoading(false);
      })
      .catch(() => setStatementLoading(false));
  };

  // Run Bulk Price Preview
  const handlePreviewBulk = async () => {
    setPreviewLoading(true);
    setPublishSuccess(null);
    try {
      const res = await api.previewBulkPrice({
        pct_change: Number(pctChange),
        dept: bulkDept || null,
        rounding_rule: roundingRule,
      });
      setPreviewItems(res.preview);
    } catch {
      setPreviewItems([]);
    } finally {
      setPreviewLoading(false);
    }
  };

  // Publish to Store Inboxes
  const handlePublishPrices = async () => {
    setPreviewLoading(true);
    try {
      const itemsToPublish = previewItems.map((p) => ({
        code: p.code,
        variant: p.variant || '000',
        description: p.description,
        dept: p.dept,
        new_price: p.new_price,
      }));

      const res = await api.applyAndPublishPrices(itemsToPublish, ['BL01', 'BL02']);
      setPublishSuccess(`Successfully updated ${res.items_updated} items and pushed XML change files to stores BL01 & BL02.`);
      fetchCatalog();
    } catch (err: any) {
      alert(`Publish error: ${err.message}`);
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-white">
            Central Price Book & In-Store Hub Sync
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Manage product prices, preview bulk adjustments with retail rounding rules, push XML changes, and audit sync acknowledgments.
          </p>
        </div>

        {/* Sub-tab pills */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-100 dark:bg-slate-800 rounded-md text-xs">
          <button
            onClick={() => setActiveTab('catalog')}
            className={`px-3 py-1 font-medium rounded transition-colors ${
              activeTab === 'catalog'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-400'
            }`}
          >
            Product Catalog
          </button>
          <button
            onClick={() => setActiveTab('sync')}
            className={`px-3 py-1 font-medium rounded transition-colors ${
              activeTab === 'sync'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-400'
            }`}
          >
            Store Hub Sync Status
          </button>
          <button
            onClick={() => setActiveTab('commercial')}
            className={`px-3 py-1 font-medium rounded transition-colors ${
              activeTab === 'commercial'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-400'
            }`}
          >
            Commercial Statements
          </button>
        </div>
      </div>

      {/* TAB 1: PRODUCT CATALOG */}
      {activeTab === 'catalog' && (
        <div className="space-y-4">
          {/* Controls: Search, Dept Filter, Bulk Adjust Button */}
          <div className="p-4 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-3">
              {/* Search */}
              <div className="flex items-center gap-2 px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md">
                <Search className="w-3.5 h-3.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search by name or code..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="bg-transparent focus:outline-none text-slate-800 dark:text-slate-200 w-44"
                />
              </div>

              {/* Department Filter */}
              <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md">
                <Filter className="w-3.5 h-3.5 text-slate-400" />
                <select
                  aria-label="Filter by department"
                  value={dept}
                  onChange={(e) => setDept(e.target.value)}
                  className="bg-transparent font-medium text-slate-700 dark:text-slate-200 focus:outline-none cursor-pointer"
                >
                  <option value="">All Departments</option>
                  {meta?.departments ? (
                    meta.departments.map((d) => (
                      <option key={d.code} value={d.code}>
                        Dept {d.code} - {d.name}
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="10">Dept 10 - Produce</option>
                      <option value="20">Dept 20 - Bakery</option>
                      <option value="30">Dept 30 - Dairy</option>
                      <option value="40">Dept 40 - Deli</option>
                    </>
                  )}
                </select>
              </div>
            </div>

            {/* Bulk Adjust Drawer Trigger */}
            <button
              onClick={() => {
                setShowBulkDrawer(true);
                handlePreviewBulk();
              }}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-medium hover:bg-slate-800 dark:hover:bg-slate-200 transition-colors shadow-xs"
            >
              <Sliders className="w-3.5 h-3.5" />
              <span>Bulk Price Adjustment</span>
            </button>
          </div>

          {/* Catalog Table */}
          <div className="p-5 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm">
            {catalogLoading ? (
              <div className="py-20 text-center text-slate-400">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900 dark:border-slate-100 mx-auto" />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400 font-medium">
                      <th className="py-2.5 px-3">Item Code</th>
                      <th className="py-2.5 px-3">Variant</th>
                      <th className="py-2.5 px-3">Product Description</th>
                      <th className="py-2.5 px-3">Department</th>
                      <th className="py-2.5 px-3 font-mono text-right">Retail Shelf Price</th>
                      <th className="py-2.5 px-3 text-center">Tax Group</th>
                      <th className="py-2.5 px-3 text-center">Restrictions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {catalogItems.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                        <td className="py-2.5 px-3 font-mono font-medium">{item.code}</td>
                        <td className="py-2.5 px-3 font-mono text-slate-400">{item.variant}</td>
                        <td className="py-2.5 px-3 font-medium text-slate-900 dark:text-white">
                          {item.description}
                        </td>
                        <td className="py-2.5 px-3">Dept {item.dept}</td>
                        <td className="py-2.5 px-3 font-mono text-right font-semibold text-slate-900 dark:text-white">
                          ${item.price.toFixed(2)}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <Badge variant="neutral" size="sm">
                            Group {item.tax_group}
                          </Badge>
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          {item.min_age ? (
                            <Badge variant="warning" size="sm" tooltipText={`Customer must be at least ${item.min_age} years old`}>
                              Age {item.min_age}+
                            </Badge>
                          ) : (
                            <span className="text-[10px] text-slate-400">Standard</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: STORE HUB SYNC STATUS */}
      {activeTab === 'sync' && (
        <div className="p-5 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
                In-Store Hub Sync Monitor
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Tracking outbound XML price changes, store acknowledgments (ACK), and error rejections (REJ)
              </p>
            </div>
            <button
              onClick={fetchSyncStatus}
              className="p-1.5 rounded border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-slate-900 dark:hover:text-white"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {syncLoading ? (
            <div className="py-16 text-center text-slate-400">Loading sync status...</div>
          ) : syncHistory.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-400">
              No price change batches published recently. All stores are in sync with the central master catalog.
            </div>
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              {syncHistory.map((s, idx) => {
                const isAck = s.status === 'APPLIED';
                return (
                  <div key={idx} className="py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs">
                    <div className="flex items-start gap-2.5">
                      {isAck ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                      ) : (
                        <AlertOctagon className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                      )}
                      <div>
                        <div className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
                          <span>{s.file_name}</span>
                          <Badge variant={isAck ? 'success' : 'danger'} size="sm">
                            {isAck ? 'APPLIED (ACK)' : 'REJECTED (REJ)'}
                          </Badge>
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                          Store: {s.store_id} • Change ID: {s.change_id} • Processed: {new Date(s.processed_at).toLocaleString()}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-[11px] font-mono font-medium text-slate-700 dark:text-slate-300">
                        {s.items?.length || 0} items updated
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: COMMERCIAL BUSINESS STATEMENTS */}
      {activeTab === 'commercial' && (
        <div className="space-y-4">
          <div className="p-4 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm flex items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <Building className="w-4 h-4 text-slate-500" />
              <span className="font-semibold text-slate-800 dark:text-slate-200">Select Commercial Account:</span>
              <select
                aria-label="Select commercial business account"
                value={selectedAccount}
                onChange={(e) => setSelectedAccount(e.target.value)}
                className="px-2.5 py-1 rounded bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 font-medium text-slate-800 dark:text-slate-200"
              >
                {meta?.business_accounts && meta.business_accounts.length > 0 ? (
                  meta.business_accounts.map((acc) => (
                    <option key={acc.account_id} value={acc.account_id}>
                      {acc.account_id} — {acc.business_name} {acc.terms ? `(${acc.terms})` : ''}
                    </option>
                  ))
                ) : (
                  <option value="BA-0001">BA-0001 — Sunrise Cafe & Bakery</option>
                )}
              </select>
            </div>
          </div>

          {statementLoading || !statement ? (
            <div className="py-16 text-center text-slate-400">Loading commercial account statement...</div>
          ) : (
            <div className="p-6 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm space-y-6">
              {/* Statement Header */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
                <div>
                  <h2 className="text-base font-bold text-slate-900 dark:text-white">
                    {statement.account_name}
                  </h2>
                  <div className="text-xs text-slate-500 font-mono mt-0.5">
                    Account: {statement.account_id} • Billing Month: {statement.month}
                  </div>
                </div>
                <div className="flex gap-4 text-xs font-mono">
                  <div className="p-3 rounded bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                    <div className="text-[10px] text-slate-400 font-sans uppercase">Credit Terms</div>
                    <div className="font-semibold mt-0.5 text-slate-900 dark:text-white">{statement.payment_terms}</div>
                  </div>
                  <div className="p-3 rounded bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                    <div className="text-[10px] text-slate-400 font-sans uppercase">Credit Limit</div>
                    <div className="font-semibold mt-0.5 text-slate-900 dark:text-white">${statement.credit_limit.toFixed(2)}</div>
                  </div>
                  <div className="p-3 rounded bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900">
                    <div className="text-[10px] text-blue-600 dark:text-blue-400 font-sans uppercase">Balance Due</div>
                    <div className="font-bold mt-0.5 text-blue-900 dark:text-blue-200">${statement.closing_balance.toFixed(2)}</div>
                  </div>
                </div>
              </div>

              {/* Transactions Ledger */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                  Monthly Purchase Ledger
                </h3>
                {statement.transactions.length === 0 ? (
                  <div className="py-6 text-center text-xs text-slate-400">No transactions recorded for this billing cycle.</div>
                ) : (
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400">
                        <th className="py-2 px-3">Date</th>
                        <th className="py-2 px-3">Receipt #</th>
                        <th className="py-2 px-3">Transaction Type</th>
                        <th className="py-2 px-3 font-mono text-right">Charge Amount</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {statement.transactions.map((tx, idx) => (
                        <tr key={idx}>
                          <td className="py-2 px-3 font-mono">{tx.business_date}</td>
                          <td className="py-2 px-3 font-mono">#{tx.seq}</td>
                          <td className="py-2 px-3 font-medium">{tx.type}</td>
                          <td className="py-2 px-3 font-mono text-right font-semibold">${tx.amount.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* BULK PRICE ADJUSTMENT MODAL / DRAWER */}
      {showBulkDrawer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-2xl p-6 text-xs max-h-[90vh] overflow-y-auto space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <div>
                <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                  Bulk Price Adjustment Assistant
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Calculate price adjustments with retail psychology rounding rules before sending to registers.
                </p>
              </div>
              <button
                onClick={() => setShowBulkDrawer(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 font-bold"
              >
                ✕
              </button>
            </div>

            {/* Inputs */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-300 mb-1">
                  Percentage Change (%)
                </label>
                <input
                  type="number"
                  step="0.5"
                  value={pctChange}
                  onChange={(e) => setPctChange(Number(e.target.value))}
                  className="w-full px-2.5 py-1.5 rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white font-mono"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-300 mb-1">
                  Department
                </label>
                <select
                  value={bulkDept}
                  onChange={(e) => setBulkDept(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white font-medium"
                >
                  <option value="">All Departments</option>
                  <option value="10">Dept 10 - Produce</option>
                  <option value="20">Dept 20 - Bakery</option>
                  <option value="30">Dept 30 - Dairy</option>
                  <option value="40">Dept 40 - Deli</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-300 mb-1">
                  Retail Rounding Rule
                </label>
                <select
                  value={roundingRule}
                  onChange={(e) => setRoundingRule(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white font-medium"
                >
                  <option value="ROUND_UP_9">End in 9 Cents ($4.29)</option>
                  <option value="ROUND_99">Standard 99 Cents ($4.99)</option>
                  <option value="ROUND_STANDARD">Exact Penny Math ($4.44)</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={handlePreviewBulk}
                className="px-3 py-1.5 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-medium"
              >
                Re-calculate Preview
              </button>
            </div>

            {/* Notification */}
            {publishSuccess && (
              <div className="p-3 rounded bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300">
                {publishSuccess}
              </div>
            )}

            {/* Diff Preview Table */}
            <div className="border border-slate-200 dark:border-slate-800 rounded-md overflow-hidden">
              <div className="p-2.5 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 font-medium flex justify-between items-center">
                <span>Calculated Diff Preview ({previewItems.length} items affected)</span>
              </div>
              <div className="max-h-56 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400">
                      <th className="py-2 px-3">Item</th>
                      <th className="py-2 px-3 font-mono text-right">Current Price</th>
                      <th className="py-2 px-3 font-mono text-right">New Price</th>
                      <th className="py-2 px-3 font-mono text-right">Dollar Diff</th>
                      <th className="py-2 px-3 font-mono text-right">% Shift</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {previewItems.map((p) => (
                      <tr key={p.code}>
                        <td className="py-2 px-3 font-medium">
                          {p.description} <span className="font-mono text-slate-400 text-[10px]">({p.code})</span>
                        </td>
                        <td className="py-2 px-3 font-mono text-right">${p.old_price.toFixed(2)}</td>
                        <td className="py-2 px-3 font-mono text-right font-semibold text-slate-900 dark:text-white">
                          ${p.new_price.toFixed(2)}
                        </td>
                        <td className="py-2 px-3 font-mono text-right text-emerald-600 dark:text-emerald-400">
                          +${p.diff.toFixed(2)}
                        </td>
                        <td className="py-2 px-3 font-mono text-right">{p.pct_change.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Publish Action Button */}
            <div className="pt-2 flex justify-end gap-2 border-t border-slate-200 dark:border-slate-800">
              <button
                onClick={() => setShowBulkDrawer(false)}
                className="px-3 py-1.5 rounded border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300"
              >
                Cancel
              </button>
              <button
                disabled={previewLoading || previewItems.length === 0}
                onClick={handlePublishPrices}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white font-medium shadow-xs disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>Publish to Store Hubs (XML)</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
