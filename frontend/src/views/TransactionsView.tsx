import React, { useEffect, useState } from 'react';
import {
  Receipt,
  Filter,
  X,
  Ban,
  CreditCard,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import type {
  TransactionSummaryItem,
  TransactionDetailResponse,
} from '../types';
import { Badge } from '../components/common/Badge';

export const TransactionsView: React.FC = () => {
  const { storeId, businessDate } = useApp();
  const [items, setItems] = useState<TransactionSummaryItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [deviceId, setDeviceId] = useState<string>('');
  const [tenderType, setTenderType] = useState<string>('');
  const [hasVoids, setHasVoids] = useState<boolean>(false);
  const [offset, setOffset] = useState<number>(0);
  const limit = 30;

  // Selected Transaction for Virtual Receipt Modal
  const [selectedTxId, setSelectedTxId] = useState<string | null>(null);
  const [receiptDetail, setReceiptDetail] = useState<TransactionDetailResponse | null>(null);
  const [receiptLoading, setReceiptLoading] = useState<boolean>(false);

  const fetchTransactions = () => {
    setLoading(true);
    setError(null);

    api
      .getTransactions({
        store_id: storeId,
        date: businessDate,
        device_id: deviceId || undefined,
        tender_type: tenderType || undefined,
        has_voids: hasVoids ? true : undefined,
        limit,
        offset,
      })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load transaction ledger.');
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchTransactions();
  }, [storeId, businessDate, deviceId, tenderType, hasVoids, offset]);

  // Load Receipt Detail
  const handleOpenReceipt = async (txId: string) => {
    setSelectedTxId(txId);
    setReceiptLoading(true);
    try {
      const detail = await api.getTransactionDetail(txId);
      setReceiptDetail(detail);
    } catch {
      setReceiptDetail(null);
    } finally {
      setReceiptLoading(false);
    }
  };

  const handleCloseReceipt = () => {
    setSelectedTxId(null);
    setReceiptDetail(null);
  };

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-white">
            Transaction Ledger & Virtual POS Receipts
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Audit individual customer sales, checkouts with cancelled items, and digital receipt drilldowns.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="neutral" size="sm">
            <span>{total} Total Transactions Found</span>
          </Badge>
        </div>
      </div>

      {/* Filter Command Strip */}
      <div className="p-4 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          {/* Terminal Filter */}
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              aria-label="Filter by register terminal"
              value={deviceId}
              onChange={(e) => {
                setDeviceId(e.target.value);
                setOffset(0);
              }}
              className="bg-transparent font-medium text-slate-700 dark:text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="">All Terminals</option>
              <option value="REG-01">Register 01 (REG-01)</option>
              <option value="REG-02">Register 02 (REG-02)</option>
              <option value="SCO-01">Self-Checkout 01 (SCO-01)</option>
              <option value="SCO-02">Self-Checkout 02 (SCO-02)</option>
            </select>
          </div>

          {/* Payment Tender Filter */}
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md">
            <CreditCard className="w-3.5 h-3.5 text-slate-400" />
            <select
              aria-label="Filter by payment method"
              value={tenderType}
              onChange={(e) => {
                setTenderType(e.target.value);
                setOffset(0);
              }}
              className="bg-transparent font-medium text-slate-700 dark:text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="">All Payment Types</option>
              <option value="CASH">Cash</option>
              <option value="CARD">Credit / Debit Card</option>
              <option value="ACCOUNT">Business Account</option>
              <option value="GIFT_CARD">Gift Card</option>
            </select>
          </div>

          {/* Voids Toggle Pill */}
          <button
            onClick={() => {
              setHasVoids(!hasVoids);
              setOffset(0);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition-colors border ${
              hasVoids
                ? 'bg-rose-50 text-rose-800 border-rose-300 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800'
                : 'bg-slate-50 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700'
            }`}
          >
            <Ban className="w-3.5 h-3.5 text-rose-500" />
            <span>Only Transactions with Cancelled Items</span>
          </button>
        </div>

        {/* Pagination buttons */}
        <div className="flex items-center gap-2">
          <button
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}
            className="px-2.5 py-1 rounded border border-slate-200 dark:border-slate-700 disabled:opacity-40 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
          >
            Previous
          </button>
          <span className="text-slate-500 font-mono text-[11px]">
            {offset + 1} - {Math.min(offset + limit, total)} of {total}
          </span>
          <button
            disabled={offset + limit >= total}
            onClick={() => setOffset(offset + limit)}
            className="px-2.5 py-1 rounded border border-slate-200 dark:border-slate-700 disabled:opacity-40 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
          >
            Next
          </button>
        </div>
      </div>

      {/* Transactions High-Density Table */}
      <div className="p-5 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center py-20 text-slate-400">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900 dark:border-slate-100" />
          </div>
        ) : error ? (
          <div className="py-8 text-center text-xs text-rose-600">{error}</div>
        ) : items.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-400">
            No transactions match the selected filter criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400 font-medium">
                  <th className="py-2.5 px-3">Receipt #</th>
                  <th className="py-2.5 px-3">Time</th>
                  <th className="py-2.5 px-3">Store</th>
                  <th className="py-2.5 px-3">Terminal</th>
                  <th className="py-2.5 px-3">Cashier</th>
                  <th className="py-2.5 px-3">Payment</th>
                  <th className="py-2.5 px-3 text-center">Items</th>
                  <th className="py-2.5 px-3 font-mono text-right">Net Sales</th>
                  <th className="py-2.5 px-3 font-mono text-right">Total Paid</th>
                  <th className="py-2.5 px-3 text-center">Audit Badges</th>
                  <th className="py-2.5 px-3 text-right">Receipt</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {items.map((tx) => {
                  const timeFormatted = tx.start_time
                    ? new Date(tx.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                    : '-';
                  return (
                    <tr
                      key={tx.id}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors cursor-pointer group"
                      onClick={() => handleOpenReceipt(tx.id)}
                    >
                      <td className="py-2.5 px-3 font-mono font-medium text-slate-900 dark:text-white">
                        #{tx.seq}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-slate-500">{timeFormatted}</td>
                      <td className="py-2.5 px-3 font-medium">{tx.store_id}</td>
                      <td className="py-2.5 px-3 font-mono">{tx.device_id}</td>
                      <td className="py-2.5 px-3">{tx.staff_id}</td>
                      <td className="py-2.5 px-3">
                        <div className="flex gap-1">
                          {tx.tenders.map((t, idx) => (
                            <Badge key={idx} variant="neutral" size="sm">
                              {t.tender_type}
                            </Badge>
                          ))}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-center font-mono">{tx.item_count}</td>
                      <td className="py-2.5 px-3 font-mono text-right">${tx.net_amount.toFixed(2)}</td>
                      <td className="py-2.5 px-3 font-mono text-right font-semibold text-slate-900 dark:text-white">
                        ${tx.grand_total.toFixed(2)}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <div className="flex items-center justify-center gap-1">
                          {tx.void_count > 0 && (
                            <Badge variant="danger" size="sm" tooltipText={`${tx.void_count} items were cancelled from cart`}>
                              {tx.void_count} Voids
                            </Badge>
                          )}
                          {tx.is_flagged && (
                            <Badge variant="warning" size="sm" tooltipText={tx.flag_reason || 'Flagged for audit'}>
                              Review
                            </Badge>
                          )}
                          {tx.void_count === 0 && !tx.is_flagged && (
                            <span className="text-[10px] text-slate-400">Clean</span>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenReceipt(tx.id);
                          }}
                          className="px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium inline-flex items-center gap-1 text-[11px]"
                        >
                          <Receipt className="w-3 h-3 text-slate-500" />
                          <span>View Slip</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Virtual POS Thermal Receipt Modal */}
      {selectedTxId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="relative w-full max-w-md bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-2xl p-6 font-mono text-xs max-h-[90vh] overflow-y-auto">
            {/* Modal Close Button */}
            <button
              onClick={handleCloseReceipt}
              className="absolute top-4 right-4 p-1 rounded-md text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>

            {receiptLoading || !receiptDetail ? (
              <div className="py-16 text-center text-slate-400">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900 dark:border-slate-100 mx-auto" />
                <p className="mt-3">Fetching register receipt...</p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Receipt Thermal Header */}
                <div className="text-center border-b border-dashed border-slate-300 dark:border-slate-700 pb-3">
                  <div className="text-base font-bold tracking-tight text-slate-900 dark:text-white uppercase">
                    Brightleaf Market
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Store {receiptDetail.store_id} • Register {receiptDetail.device_id}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Cashier: {receiptDetail.staff_id} • Shift {receiptDetail.shift}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1">
                    Receipt #{receiptDetail.seq} • {new Date(receiptDetail.start_time).toLocaleString()}
                  </div>
                </div>

                {/* Line Items Table */}
                <div className="divide-y divide-slate-100 dark:divide-slate-800">
                  <div className="flex justify-between text-[11px] font-semibold text-slate-400 pb-1">
                    <span>Item & Qty</span>
                    <span>Total</span>
                  </div>
                  {receiptDetail.lines.map((line, idx) => (
                    <div
                      key={idx}
                      className={`py-1.5 flex justify-between items-start ${
                        line.is_void ? 'text-rose-500 line-through opacity-75' : 'text-slate-800 dark:text-slate-200'
                      }`}
                    >
                      <div>
                        <div className="font-medium">
                          {line.description}
                          {line.is_void && (
                            <span className="ml-1 text-[10px] no-underline inline-block px-1 rounded bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300">
                              CANCELLED
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {line.qty} @ ${line.unit_price.toFixed(2)} ea • Dept {line.dept}
                        </div>
                      </div>
                      <div className="font-semibold text-right">
                        ${line.amount.toFixed(2)}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Subtotals & Taxes */}
                <div className="border-t border-dashed border-slate-300 dark:border-slate-700 pt-3 space-y-1 text-slate-600 dark:text-slate-300">
                  <div className="flex justify-between">
                    <span>Subtotal (Net):</span>
                    <span className="font-medium">${receiptDetail.net_amount.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Sales Tax:</span>
                    <span className="font-medium">${receiptDetail.tax_amount.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-sm font-bold text-slate-900 dark:text-white pt-1 border-t border-slate-200 dark:border-slate-800">
                    <span>Grand Total:</span>
                    <span>${receiptDetail.grand_total.toFixed(2)}</span>
                  </div>
                </div>

                {/* Payment Tender Slip */}
                <div className="border-t border-dashed border-slate-300 dark:border-slate-700 pt-3 space-y-1 text-slate-500 text-[11px]">
                  <div className="font-semibold text-slate-700 dark:text-slate-300 uppercase text-[10px] tracking-wider">
                    Payment Method
                  </div>
                  {receiptDetail.tenders.map((t, idx) => (
                    <div key={idx} className="flex justify-between items-center">
                      <span>
                        {t.tender_type} {t.card_type ? `(${t.card_type} •••• ${t.last4 || '4242'})` : ''}
                      </span>
                      <span className="font-medium text-slate-800 dark:text-slate-200">
                        ${t.amount.toFixed(2)}
                      </span>
                    </div>
                  ))}
                  {receiptDetail.tenders[0]?.auth_code && (
                    <div className="text-[10px] text-slate-400">
                      Auth Code: {receiptDetail.tenders[0].auth_code}
                    </div>
                  )}
                </div>

                {/* Receipt Footer */}
                <div className="text-center pt-3 border-t border-dashed border-slate-300 dark:border-slate-700 text-[10px] text-slate-400">
                  Thank you for shopping at Brightleaf Market!
                  <br />
                  Verified Ground Truth POS Slip
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
