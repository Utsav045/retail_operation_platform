import React from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { Header } from './components/layout/Header';
import { OverviewView } from './views/OverviewView';
import { ReconciliationView } from './views/ReconciliationView';
import { TransactionsView } from './views/TransactionsView';
import { PriceBookView } from './views/PriceBookView';
import { IntelligenceView } from './views/IntelligenceView';
import { SystemView } from './views/SystemView';

const MainContent: React.FC = () => {
  const { activeView } = useApp();

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {activeView === 'overview' && <OverviewView />}
      {activeView === 'reconciliation' && <ReconciliationView />}
      {activeView === 'transactions' && <TransactionsView />}
      {activeView === 'pricing' && <PriceBookView />}
      {activeView === 'intelligence' && <IntelligenceView />}
      {activeView === 'system' && <SystemView />}
    </main>
  );
};

export function App() {
  return (
    <AppProvider>
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-200">
        <Header />
        <MainContent />
      </div>
    </AppProvider>
  );
}

export default App;
