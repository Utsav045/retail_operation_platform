import React, { useEffect, useState } from 'react';
import {
  Store,
  Calendar,
  Sun,
  Moon,
  Activity,
  BarChart3,
  Scale,
  Receipt,
  Tag,
  Sparkles,
  Server,
  LogOut,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { useAuth } from '../../context/AuthContext';
import { Tooltip } from '../common/Tooltip';
import { api } from '../../services/api';
import type { LiveStatusResponse } from '../../types';

export const Header: React.FC = () => {
  const { storeId, setStoreId, businessDate, setBusinessDate, isDark, toggleTheme, activeView, setActiveView, meta } = useApp();
  const { user, logout } = useAuth();
  const [liveStatus, setLiveStatus] = useState<LiveStatusResponse | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchLiveStatus = async () => {
    try {
      setIsRefreshing(true);
      const res = await api.getLiveStatus();
      setLiveStatus(res);
    } catch {
      // silently handle offline/polling error
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchLiveStatus();
    const interval = setInterval(fetchLiveStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { id: 'overview', label: 'Store Pulse', icon: BarChart3, tooltip: 'Operations overview, hourly sales velocity, and exception watch list' },
    { id: 'reconciliation', label: 'Register Audit', icon: Scale, tooltip: 'Daily EOD ground-truth audit and cashier till cash drawer balancing' },
    { id: 'transactions', label: 'Transactions', icon: Receipt, tooltip: 'Search transaction ledger and view virtual POS receipts' },
    { id: 'pricing', label: 'Price Book', icon: Tag, tooltip: 'Central catalog management, bulk rounding adjustments, and in-store hub sync' },
    { id: 'intelligence', label: 'AI Intelligence', icon: Sparkles, tooltip: 'Supplier invoice verification, 35% margin sync, and Loss Prevention radar' },
    { id: 'system', label: 'System Health', icon: Server, tooltip: 'Store node connection health and quarantined batch vault' },
  ];



  return (
    <header className="sticky top-0 z-40 bg-white/95 dark:bg-slate-900/95 backdrop-blur border-b border-slate-200 dark:border-slate-800 transition-colors">
      {/* Top Global Command Strip */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14 gap-4">
          {/* Logo & Platform Name */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-md bg-slate-900 dark:bg-slate-100 flex items-center justify-center text-white dark:text-slate-900 font-semibold text-sm tracking-tight shadow-sm">
              BL
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-900 dark:text-white text-sm tracking-tight">
                  Brightleaf Market
                </span>
                <span className="hidden sm:inline-block text-[10px] uppercase font-mono tracking-wider px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                  Operations Suite
                </span>
              </div>
            </div>
          </div>

          {/* Controls: Store Selector, Date Picker, Theme Toggle, Live Status */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Store Selector */}
            <Tooltip content="Filter operations metrics by store location or view aggregate network">
              <div className="flex items-center gap-1.5 px-2.5 py-1 text-xs bg-slate-100 dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 rounded-md">
                <Store className="w-3.5 h-3.5 text-slate-500" />
                <select
                  aria-label="Filter by store location"
                  value={storeId}
                  onChange={(e) => setStoreId(e.target.value)}
                  className="bg-transparent font-medium text-slate-700 dark:text-slate-200 focus:outline-none cursor-pointer"
                >
                  <option value="ALL">All Stores (Network)</option>
                  {meta?.stores ? (
                    meta.stores.map((s) => (
                      <option key={s.store_id} value={s.store_id}>
                        {s.store_id} - {s.name} ({s.city})
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="BL01">BL01 - Downtown (Seattle)</option>
                      <option value="BL02">BL02 - Westside (Portland)</option>
                    </>
                  )}
                </select>
              </div>
            </Tooltip>

            {/* Quick Date Presets & Picker */}
            <div className="hidden md:flex items-center gap-1 bg-slate-100 dark:bg-slate-800/90 p-0.5 border border-slate-200 dark:border-slate-700 rounded-md">
              <div className="flex items-center px-1.5 text-slate-400">
                <Calendar className="w-3.5 h-3.5" />
              </div>
              {meta?.business_dates && meta.business_dates.slice(0, 4).map((d) => (
                <button
                  key={d}
                  onClick={() => setBusinessDate(d)}
                  className={`px-2 py-0.5 text-xs font-medium rounded transition-colors ${
                    businessDate === d
                      ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  {d.slice(5)}
                </button>
              ))}
              <input
                type="date"
                aria-label="Select custom business date"
                value={businessDate}
                onChange={(e) => setBusinessDate(e.target.value)}
                className="bg-transparent text-xs font-mono text-slate-700 dark:text-slate-300 px-1.5 py-0.5 focus:outline-none cursor-pointer"
              />
            </div>

            {/* Live Hub Sync Indicator */}
            <Tooltip content={liveStatus ? `System Healthy. Total files ingested: ${liveStatus.total_files_ingested}. Quarantined: ${liveStatus.quarantined_files_count}` : 'Connecting to store hubs...'}>
              <button
                onClick={fetchLiveStatus}
                className="flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 text-emerald-800 dark:text-emerald-300 transition-colors"
              >
                <Activity className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
                <span className="hidden lg:inline font-medium">Hub Live</span>
              </button>
            </Tooltip>

            {/* Theme Toggle (Light / Dark) */}
            <Tooltip content={isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme'}>
              <button
                onClick={toggleTheme}
                aria-label="Toggle light or dark theme"
                className="p-1.5 rounded-md text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 transition-colors"
              >
                {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              </button>
            </Tooltip>

            {/* Authenticated User Profile & Sign Out */}
            {user && (
              <div className="flex items-center gap-2 pl-2 border-l border-slate-200 dark:border-slate-800">
                <Tooltip content={`Signed in as ${user.name} (${user.email})`}>
                  <div className="flex items-center gap-2 px-2 py-1 rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs">
                    <div className="w-5 h-5 rounded-full bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-bold flex items-center justify-center text-[10px]">
                      {user.name.charAt(0)}
                    </div>
                    <span className="hidden sm:inline font-medium text-slate-700 dark:text-slate-200">
                      {user.name}
                    </span>
                  </div>
                </Tooltip>

                <Tooltip content="Sign Out from Platform">
                  <button
                    onClick={logout}
                    aria-label="Sign Out"
                    className="p-1.5 rounded-md text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 border border-slate-200 dark:border-slate-700 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                  </button>
                </Tooltip>
              </div>
            )}
          </div>
        </div>

        {/* View Navigation Tab Strip */}
        <nav className="flex space-x-1 overflow-x-auto py-1 scrollbar-none border-t border-slate-100 dark:border-slate-800">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;
            return (
              <Tooltip key={item.id} content={item.tooltip}>
                <button
                  onClick={() => setActiveView(item.id)}
                  className={`flex items-center gap-2 px-3 py-2 text-xs font-medium rounded-md whitespace-nowrap transition-all ${
                    isActive
                      ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{item.label}</span>
                </button>
              </Tooltip>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
