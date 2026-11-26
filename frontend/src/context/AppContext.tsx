import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';
import type { PlatformMetaOptions } from '../types';

interface AppContextType {
  storeId: string;
  setStoreId: (id: string) => void;
  businessDate: string;
  setBusinessDate: (date: string) => void;
  isDark: boolean;
  toggleTheme: () => void;
  activeView: string;
  setActiveView: (view: string) => void;
  meta: PlatformMetaOptions | null;
  refreshMeta: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [storeId, setStoreId] = useState<string>('ALL');
  const [businessDate, setBusinessDate] = useState<string>('2026-10-04');
  const [activeView, setActiveView] = useState<string>('overview');
  const [meta, setMeta] = useState<PlatformMetaOptions | null>(null);

  const [isDark, setIsDark] = useState<boolean>(() => {
    return localStorage.getItem('theme') === 'dark';
  });

  const fetchMeta = () => {
    api
      .getMetaOptions()
      .then((res) => {
        setMeta(res);
        // Automatically default businessDate to latest if not set
        if (res.business_dates && res.business_dates.length > 0 && !res.business_dates.includes(businessDate)) {
          setBusinessDate(res.business_dates[0]);
        }
      })
      .catch(() => {
        // Fallback gracefully if offline
      });
  };

  useEffect(() => {
    fetchMeta();
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      root.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  const toggleTheme = () => setIsDark((prev) => !prev);

  return (
    <AppContext.Provider
      value={{
        storeId,
        setStoreId,
        businessDate,
        setBusinessDate,
        isDark,
        toggleTheme,
        activeView,
        setActiveView,
        meta,
        refreshMeta: fetchMeta,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
