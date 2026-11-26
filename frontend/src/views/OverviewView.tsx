import React, { useEffect, useState } from 'react';
import {
  DollarSign,
  Users,
  ShoppingBag,
  CreditCard,
  AlertTriangle,
  Clock,
  TrendingUp,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import type { DashboardDailyResponse } from '../types';
import { MetricCard } from '../components/common/MetricCard';
import { Badge } from '../components/common/Badge';

export const OverviewView: React.FC = () => {
  const { storeId, businessDate } = useApp();
  const [data, setData] = useState<DashboardDailyResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    api
      .getDashboardDaily(businessDate, storeId)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to load daily operations data.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [storeId, businessDate]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900 dark:border-slate-100" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 rounded-lg text-rose-800 dark:text-rose-300 text-sm">
        <p className="font-semibold">Unable to load daily pulse</p>
        <p className="mt-1">{error || 'No telemetry available for selected store/date combination.'}</p>
      </div>
    );
  }

  const { headline, sales_by_hour, tenders_breakdown, departments_breakdown, watch_list } = data;

  // Max sales calculation for responsive SVG chart
  const maxHourlySales = Math.max(...sales_by_hour.map((h) => h.sales), 100);

  const counterPct = headline.total_sales > 0 ? (headline.counter_sales / headline.total_sales) * 100 : 0;
  const scoPct = headline.total_sales > 0 ? (headline.self_checkout_sales / headline.total_sales) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-white">
            Daily Store Pulse & Operations
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Real-time turnover velocity, terminal split, tender mix, and security watch list.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="neutral" size="sm" tooltipText="Operating business date for current metrics">
            <Clock className="w-3 h-3 text-slate-400" />
            <span>Date: {businessDate}</span>
          </Badge>
          <Badge variant="info" size="sm" tooltipText="Active store scope">
            <span>Location: {storeId === 'ALL' ? 'All Stores (Network)' : storeId}</span>
          </Badge>
        </div>
      </div>

      {/* Top 5 Headline Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          title="Total Gross Sales"
          value={`$${headline.total_sales.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          subValue={`${headline.transaction_count} sales`}
          tooltipText="Total revenue rung up across all cashiers and self-checkouts today"
          icon={DollarSign}
        />
        <MetricCard
          title="Cashier vs SCO Split"
          value={`${counterPct.toFixed(0)}% / ${scoPct.toFixed(0)}%`}
          subValue={`$${headline.counter_sales.toFixed(0)} / $${headline.self_checkout_sales.toFixed(0)}`}
          tooltipText="Breakdown of sales conducted at traditional cashier counters versus self-checkout kiosks"
          icon={TrendingUp}
        />
        <MetricCard
          title="Transactions"
          value={headline.transaction_count}
          subValue="Completed"
          tooltipText="Total number of finished customer checkout transactions"
          icon={Users}
        />
        <MetricCard
          title="Average Basket"
          value={`$${headline.average_basket.toFixed(2)}`}
          subValue="Per checkout"
          tooltipText="Average dollar amount spent per customer transaction"
          icon={ShoppingBag}
        />
        <MetricCard
          title="Gift Card Loads"
          value={`$${headline.gift_card_loads.toFixed(2)}`}
          subValue="Activated"
          tooltipText="Total new funds loaded and activated onto Brightleaf gift cards"
          icon={CreditCard}
        />
      </div>

      {/* Hourly Sales Velocity SVG Chart */}
      <div className="p-5 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
              Hourly Turnover Velocity
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Customer checkout volume across operating hours (8:00 AM to 11:00 PM)
            </p>
          </div>
          <div className="text-xs font-mono text-slate-500 dark:text-slate-400">
            Peak Capacity: ${maxHourlySales.toFixed(0)}
          </div>
        </div>

        {/* Responsive Bar Grid */}
        <div className="h-44 flex items-end gap-1 sm:gap-2 pt-6 pb-2 px-2 border-b border-slate-100 dark:border-slate-800">
          {sales_by_hour.map((h) => {
            const heightPct = (h.sales / maxHourlySales) * 100;
            return (
              <div key={h.hour} className="flex-1 flex flex-col items-center gap-1 group relative">
                {/* Tooltip on hover */}
                <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute bottom-full mb-2 z-20 pointer-events-none bg-slate-900 text-white text-[11px] rounded px-2 py-1 font-mono shadow-md whitespace-nowrap">
                  <div>{h.hour}:00 — ${(h.sales).toFixed(2)}</div>
                  <div className="text-[10px] text-slate-300">{h.tx_count} customer checkouts</div>
                </div>

                {/* Animated bar */}
                <div
                  style={{ height: `${Math.max(heightPct, 4)}%` }}
                  className={`w-full rounded-t transition-all duration-300 ${
                    h.sales > 0
                      ? 'bg-slate-800 dark:bg-slate-200 group-hover:bg-blue-600 dark:group-hover:bg-blue-400'
                      : 'bg-slate-100 dark:bg-slate-800'
                  }`}
                />
                <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500">
                  {h.hour}h
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Grid: Tender Breakdown & Department Mix */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Payment Tenders Breakdown */}
        <div className="p-5 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
                Payment Method Breakdown
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Distribution of cash, payment cards, business accounts, and gift cards
              </p>
            </div>
          </div>
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {tenders_breakdown.map((t) => {
              const tenderShare = headline.total_sales > 0 ? (t.total_amount / headline.total_sales) * 100 : 0;
              return (
                <div key={t.tender_type} className="py-2.5 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-800 dark:text-slate-200">
                      {t.tender_type}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      ({t.count} payments)
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-20 sm:w-28 bg-slate-100 dark:bg-slate-800 rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-slate-800 dark:bg-slate-200 h-full rounded-full"
                        style={{ width: `${Math.min(tenderShare, 100)}%` }}
                      />
                    </div>
                    <span className="font-mono font-medium text-slate-900 dark:text-white w-20 text-right">
                      ${t.total_amount.toFixed(2)}
                    </span>
                    <span className="text-slate-400 text-[11px] w-10 text-right font-mono">
                      {tenderShare.toFixed(1)}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Department Sales Breakdown */}
        <div className="p-5 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
                Department Performance
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Gross sales and units rung up by merchandise department
              </p>
            </div>
          </div>
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {departments_breakdown.map((d) => {
              const deptNames: Record<string, string> = {
                '10': 'Produce & Fresh Fruits',
                '20': 'Bakery & Artisan Bread',
                '30': 'Dairy, Milk & Eggs',
                '40': 'Deli, Meats & Cheeses',
                '50': 'Pantry & Dry Grocery',
                '60': 'Beverages & Soft Drinks',
                '70': 'Snacks & Confectionery',
                '80': 'Household & General Merchandise',
              };
              const deptName = deptNames[d.dept] || `Department ${d.dept}`;
              const deptShare = headline.total_sales > 0 ? (d.total_sales / headline.total_sales) * 100 : 0;

              return (
                <div key={d.dept} className="py-2.5 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-medium text-slate-800 dark:text-slate-200">
                      {deptName}
                    </span>
                    <span className="text-[10px] text-slate-400 ml-1.5 font-mono">
                      (Dept {d.dept} • {d.item_count} items)
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-medium text-slate-900 dark:text-white w-20 text-right">
                      ${d.total_sales.toFixed(2)}
                    </span>
                    <span className="text-slate-400 text-[11px] w-10 text-right font-mono">
                      {deptShare.toFixed(1)}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Real-Time Exception Watch List */}
      <div className="p-5 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              <span>Real-Time Exception Watch List</span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Live operational feed of cashier voids, transaction cancellations, and cash drops
            </p>
          </div>
          <Badge variant="warning" size="sm" tooltipText="Total unusual events flagged for store review today">
            {watch_list.length} Events Flagged
          </Badge>
        </div>

        {watch_list.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-400">
            No operational exceptions flagged for this store and date. All registers operating cleanly.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400 font-medium">
                  <th className="py-2 px-3">Time</th>
                  <th className="py-2 px-3">Store</th>
                  <th className="py-2 px-3">Seq #</th>
                  <th className="py-2 px-3">Terminal</th>
                  <th className="py-2 px-3">Cashier</th>
                  <th className="py-2 px-3">Type</th>
                  <th className="py-2 px-3 text-right">Amount</th>
                  <th className="py-2 px-3">Audit Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {watch_list.map((evt) => (
                  <tr key={evt.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="py-2 px-3 font-mono text-slate-500">{evt.time}</td>
                    <td className="py-2 px-3 font-medium">{evt.store_id}</td>
                    <td className="py-2 px-3 font-mono">#{evt.seq}</td>
                    <td className="py-2 px-3 font-mono">{evt.device_id}</td>
                    <td className="py-2 px-3">{evt.staff_id}</td>
                    <td className="py-2 px-3">
                      <Badge variant={evt.type === 'REFUND' ? 'danger' : 'neutral'} size="sm">
                        {evt.type}
                      </Badge>
                    </td>
                    <td className="py-2 px-3 font-mono text-right font-medium">
                      ${evt.amount.toFixed(2)}
                    </td>
                    <td className="py-2 px-3 text-slate-600 dark:text-slate-300">
                      {evt.reason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
