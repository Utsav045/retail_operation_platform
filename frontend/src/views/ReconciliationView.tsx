import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  AlertCircle,
  Coins,
  FileSpreadsheet,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import type { ReconciliationReport, ShiftReconciliationItem } from '../types';
import { Badge } from '../components/common/Badge';
import { Tooltip } from '../components/common/Tooltip';

export const ReconciliationView: React.FC = () => {
  const { storeId, businessDate } = useApp();
  const effectiveStore = storeId === 'ALL' ? 'BL01' : storeId;

  const [eodReport, setEodReport] = useState<ReconciliationReport | null>(null);
  const [shifts, setShifts] = useState<ShiftReconciliationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    Promise.all([
      api.getEodReconciliation(effectiveStore, businessDate),
      api.getShiftReconciliation(effectiveStore, businessDate),
    ])
      .then(([eodRes, shiftRes]) => {
        if (isMounted) {
          setEodReport(eodRes);
          setShifts(shiftRes);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to load reconciliation data.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [effectiveStore, businessDate]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900 dark:border-slate-100" />
      </div>
    );
  }

  const statusVariant = {
    MATCHED: 'success' as const,
    MISMATCH: 'danger' as const,
    REVIEW_REQUIRED: 'warning' as const,
  };

  const statusLabel = {
    MATCHED: 'Balanced (Matched)',
    MISMATCH: 'Discrepancy Detected',
    REVIEW_REQUIRED: 'Manager Review Required',
  };

  const groundTruth = eodReport?.comparison_details?.ground_truth;
  const statedSummary = eodReport?.comparison_details?.stated_summary;

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-white">
            Daily Register & Shift Cash Audit
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Audit store server daily summary against raw transaction ground truth and balance cashier till cash drawers.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {storeId === 'ALL' && (
            <span className="text-[11px] text-slate-400 italic">
              Showing {effectiveStore} (Reconciliation is evaluated per store)
            </span>
          )}
          <Badge variant="neutral" size="sm">
            <span>Store: {effectiveStore}</span>
          </Badge>
          <Badge variant="neutral" size="sm">
            <span>Date: {businessDate}</span>
          </Badge>
        </div>
      </div>

      {error ? (
        <div className="p-6 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-600 dark:text-slate-300 text-xs">
          No reconciliation report generated yet for store {effectiveStore} on {businessDate}. Run daily EOD ingestion to compute ground truth comparison.
        </div>
      ) : (
        <>
          {/* Top Audit Status Summary Card */}
          <div className="p-5 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div className="flex items-start gap-3">
                {eodReport?.status === 'MATCHED' ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
                )}
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
                      End-of-Day Store Audit Status
                    </h2>
                    {eodReport && (
                      <Badge variant={statusVariant[eodReport.status]} size="sm">
                        {statusLabel[eodReport.status]}
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 max-w-3xl">
                    {eodReport?.root_cause_analysis || 'All scanned register sales balance with the store server summary.'}
                  </p>
                </div>
              </div>

              {/* Quick Delta Badges */}
              <div className="flex items-center gap-3 font-mono text-xs">
                <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <div className="text-[10px] uppercase text-slate-400 font-sans">Net Sales Diff</div>
                  <div className={`font-semibold mt-0.5 ${eodReport && eodReport.net_sales_diff !== 0 ? 'text-rose-600 dark:text-rose-400' : 'text-slate-700 dark:text-slate-200'}`}>
                    ${eodReport?.net_sales_diff.toFixed(2)}
                  </div>
                </div>
                <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <div className="text-[10px] uppercase text-slate-400 font-sans">Tax Diff</div>
                  <div className={`font-semibold mt-0.5 ${eodReport && eodReport.tax_diff !== 0 ? 'text-rose-600 dark:text-rose-400' : 'text-slate-700 dark:text-slate-200'}`}>
                    ${eodReport?.tax_diff.toFixed(2)}
                  </div>
                </div>
                <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <div className="text-[10px] uppercase text-slate-400 font-sans">Grand Total Diff</div>
                  <div className={`font-semibold mt-0.5 ${eodReport && eodReport.grand_total_diff !== 0 ? 'text-rose-600 dark:text-rose-400' : 'text-slate-700 dark:text-slate-200'}`}>
                    ${eodReport?.grand_total_diff.toFixed(2)}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 3-Column Ground Truth vs Store Server Comparison Table */}
          {groundTruth && statedSummary && (
            <div className="p-5 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-1.5">
                    <FileSpreadsheet className="w-4 h-4 text-slate-500" />
                    <span>Ground Truth vs Store Server Stated Totals</span>
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Comparing calculated transaction sums (ground truth) against the store computer daily report
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400 font-medium">
                      <th className="py-2.5 px-3">Financial Metric</th>
                      <th className="py-2.5 px-3 font-mono text-right">Actual Register Receipts</th>
                      <th className="py-2.5 px-3 font-mono text-right">Store Server Report</th>
                      <th className="py-2.5 px-3 font-mono text-right">Audited Difference</th>
                      <th className="py-2.5 px-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    <tr>
                      <td className="py-2.5 px-3 font-medium">Net Sales (Excluding Tax)</td>
                      <td className="py-2.5 px-3 font-mono text-right">${groundTruth.net_sales?.toFixed(2)}</td>
                      <td className="py-2.5 px-3 font-mono text-right">${statedSummary.net_sales?.toFixed(2)}</td>
                      <td className="py-2.5 px-3 font-mono text-right font-semibold">
                        ${(eodReport?.net_sales_diff || 0).toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <Badge variant={eodReport?.net_sales_diff === 0 ? 'success' : 'danger'} size="sm">
                          {eodReport?.net_sales_diff === 0 ? 'MATCH' : 'MISMATCH'}
                        </Badge>
                      </td>
                    </tr>
                    <tr>
                      <td className="py-2.5 px-3 font-medium">Sales Tax Collected</td>
                      <td className="py-2.5 px-3 font-mono text-right">${groundTruth.tax?.toFixed(2)}</td>
                      <td className="py-2.5 px-3 font-mono text-right">${statedSummary.tax?.toFixed(2)}</td>
                      <td className="py-2.5 px-3 font-mono text-right font-semibold">
                        ${(eodReport?.tax_diff || 0).toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <Badge variant={eodReport?.tax_diff === 0 ? 'success' : 'danger'} size="sm">
                          {eodReport?.tax_diff === 0 ? 'MATCH' : 'MISMATCH'}
                        </Badge>
                      </td>
                    </tr>
                    <tr className="bg-slate-50/50 dark:bg-slate-800/30">
                      <td className="py-2.5 px-3 font-semibold">Grand Total Sales</td>
                      <td className="py-2.5 px-3 font-mono text-right font-semibold">${groundTruth.grand_total?.toFixed(2)}</td>
                      <td className="py-2.5 px-3 font-mono text-right font-semibold">${statedSummary.grand_total?.toFixed(2)}</td>
                      <td className="py-2.5 px-3 font-mono text-right font-semibold">
                        ${(eodReport?.grand_total_diff || 0).toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <Badge variant={eodReport?.grand_total_diff === 0 ? 'success' : 'danger'} size="sm">
                          {eodReport?.grand_total_diff === 0 ? 'MATCH' : 'MISMATCH'}
                        </Badge>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Cashier Till Balancing Ledger (Shift Breakdown) */}
          <div className="p-5 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-1.5">
                  <Coins className="w-4 h-4 text-slate-500" />
                  <span>Cashier Till Balancing Ledger (Shift Breakdown)</span>
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Mathematical drawer reconciliation: Opening Float + Cash Tenders - Cash Refunds - Safe Drops = Expected Cash
                </p>
              </div>
              <Badge variant="neutral" size="sm">
                {shifts.length} Shifts Audited
              </Badge>
            </div>

            {shifts.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-400">
                No shift cash reports found for this store and date.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400 font-medium">
                      <th className="py-2 px-3">Terminal</th>
                      <th className="py-2 px-3">Shift #</th>
                      <th className="py-2 px-3">Cashier</th>
                      <th className="py-2 px-3 font-mono text-right">Opening Float</th>
                      <th className="py-2 px-3 font-mono text-right">Cash Sales</th>
                      <th className="py-2 px-3 font-mono text-right">Cash Refunds</th>
                      <th className="py-2 px-3 font-mono text-right">Safe Drops</th>
                      <th className="py-2 px-3 font-mono text-right">Expected Cash</th>
                      <th className="py-2 px-3 font-mono text-right">Counted Cash</th>
                      <th className="py-2 px-3 font-mono text-right">Variance</th>
                      <th className="py-2 px-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {shifts.map((s) => {
                      const isShort = s.cash_diff < 0;
                      const isOver = s.cash_diff > 0;
                      return (
                        <tr key={s.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                          <td className="py-2.5 px-3 font-mono font-medium">{s.device_id}</td>
                          <td className="py-2.5 px-3 font-mono">Shift {s.shift_no}</td>
                          <td className="py-2.5 px-3">{s.staff_id}</td>
                          <td className="py-2.5 px-3 font-mono text-right">${s.opening_float.toFixed(2)}</td>
                          <td className="py-2.5 px-3 font-mono text-right">${(s.details.cash_tenders || 0).toFixed(2)}</td>
                          <td className="py-2.5 px-3 font-mono text-right">${(s.details.cash_refunds || 0).toFixed(2)}</td>
                          <td className="py-2.5 px-3 font-mono text-right">${(s.details.cash_drops || 0).toFixed(2)}</td>
                          <td className="py-2.5 px-3 font-mono text-right font-medium">
                            <Tooltip content={s.details.formula || 'Expected cash balance in till drawer'}>
                              <span className="underline decoration-dotted cursor-help">
                                ${(s.details.expected_cash || 0).toFixed(2)}
                              </span>
                            </Tooltip>
                          </td>
                          <td className="py-2.5 px-3 font-mono text-right font-medium">
                            ${(s.details.actual_cash || s.closing_cash).toFixed(2)}
                          </td>
                          <td className={`py-2.5 px-3 font-mono text-right font-semibold ${isShort ? 'text-rose-600 dark:text-rose-400' : isOver ? 'text-blue-600 dark:text-blue-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                            {isShort ? `-$${Math.abs(s.cash_diff).toFixed(2)}` : isOver ? `+$${s.cash_diff.toFixed(2)}` : '$0.00'}
                          </td>
                          <td className="py-2.5 px-3 text-center">
                            <Badge variant={statusVariant[s.status]} size="sm" tooltipText={s.root_cause_analysis || 'Till balanced'}>
                              {s.status === 'MATCHED' ? 'Balanced' : s.status === 'MISMATCH' ? (isShort ? 'Shortage' : 'Over') : 'Review'}
                            </Badge>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
