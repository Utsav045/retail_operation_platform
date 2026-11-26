import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Header } from './components/layout/Header';
import { LoginView } from './views/LoginView';
import { OverviewView } from './views/OverviewView';
import { ReconciliationView } from './views/ReconciliationView';
import { TransactionsView } from './views/TransactionsView';
import { PriceBookView } from './views/PriceBookView';
import { IntelligenceView } from './views/IntelligenceView';
import { SystemView } from './views/SystemView';

const MainContent: React.FC = () => {
  const { activeView } = useApp();
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950 text-slate-400">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900 dark:border-slate-100" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginView />;
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-200">
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeView === 'overview' && <OverviewView />}
        {activeView === 'reconciliation' && <ReconciliationView />}
        {activeView === 'transactions' && <TransactionsView />}
        {activeView === 'pricing' && <PriceBookView />}
        {activeView === 'intelligence' && <IntelligenceView />}
        {activeView === 'system' && <SystemView />}
      </main>
    </div>
  );
};

export function App() {
  return (
    <AuthProvider>
      <AppProvider>
        <MainContent />
      </AppProvider>
    </AuthProvider>
  );
}

export default App;
