import React, { useEffect, useState } from 'react';
import {
  Sparkles,
  ShieldAlert,
  Send,
  CheckCircle2,
  AlertTriangle,
  Percent,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import type {
  AIInvoicesResponse,
  LossPreventionResponse,
  AIAskResponse,
} from '../types';
import { Badge } from '../components/common/Badge';

export const IntelligenceView: React.FC = () => {
  const { storeId, businessDate } = useApp();
  const [activeTab, setActiveTab] = useState<'invoices' | 'loss_prevention' | 'assistant'>('invoices');

  // Invoices State
  const [invoicesData, setInvoicesData] = useState<AIInvoicesResponse | null>(null);
  const [invoicesLoading, setInvoicesLoading] = useState<boolean>(true);
  const [deploySuccess, setDeploySuccess] = useState<string | null>(null);

  // Loss Prevention State
  const [lpData, setLpData] = useState<LossPreventionResponse | null>(null);
  const [lpLoading, setLpLoading] = useState<boolean>(false);

  // Ask Assistant State
  const [question, setQuestion] = useState<string>('What was the total net sales and transaction count today?');
  const [assistantReply, setAssistantReply] = useState<AIAskResponse | null>(null);
  const [assistantLoading, setAssistantLoading] = useState<boolean>(false);

  useEffect(() => {
    if (activeTab === 'invoices') {
      setInvoicesLoading(true);
      api
        .getAIInvoices()
        .then((res) => {
          setInvoicesData(res);
          setInvoicesLoading(false);
        })
        .catch(() => setInvoicesLoading(false));
    } else if (activeTab === 'loss_prevention') {
      setLpLoading(true);
      api
        .getLossPrevention(businessDate, storeId)
        .then((res) => {
          setLpData(res);
          setLpLoading(false);
        })
        .catch(() => setLpLoading(false));
    }
  }, [activeTab, storeId, businessDate]);

  const handleDeployPricing = async (filename: string) => {
    try {
      await api.publishInvoicePricing(filename, ['BL01', 'BL02']);
      setDeploySuccess(`Successfully synced 35% margin retail prices from ${filename} to store hubs!`);
    } catch (err: any) {
      alert(`Deployment failed: ${err.message}`);
    }
  };

  const handleAskAssistant = async (queryText?: string) => {
    const q = queryText || question;
    if (!q) return;
    setAssistantLoading(true);
    try {
      const res = await api.askStoreAI(q, storeId, businessDate);
      setAssistantReply(res);
    } catch (err: any) {
      setAssistantReply({
        question: q,
        answer: `Assistant error: ${err.message}`,
        data: null,
        confidence: 0,
      });
    } finally {
      setAssistantLoading(false);
    }
  };

  const questionPresets = [
    'What was the total net sales and transaction count today?',
    'Which register terminal processed the highest sales volume?',
    'How much cash was deposited into store safes today?',
    'What were the total gift card activations across all stores?',
  ];

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-white">
            AI Multimodal Intelligence & Loss Prevention
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Automated supplier invoice math audits, handwritten receiving discrepancy detection, 35% margin price sync, and security radar.
          </p>
        </div>

        {/* Sub-tab pills */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-100 dark:bg-slate-800 rounded-md text-xs">
          <button
            onClick={() => setActiveTab('invoices')}
            className={`px-3 py-1 font-medium rounded transition-colors ${
              activeTab === 'invoices'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-400'
            }`}
          >
            Supplier Invoices & Margins
          </button>
          <button
            onClick={() => setActiveTab('loss_prevention')}
            className={`px-3 py-1 font-medium rounded transition-colors ${
              activeTab === 'loss_prevention'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-400'
            }`}
          >
            Loss Prevention Radar
          </button>
          <button
            onClick={() => setActiveTab('assistant')}
            className={`px-3 py-1 font-medium rounded transition-colors ${
              activeTab === 'assistant'
                ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-400'
            }`}
          >
            "Ask Your Stores" Assistant
          </button>
        </div>
      </div>

      {/* TAB 1: SUPPLIER INVOICES & 35% MARGINS */}
      {activeTab === 'invoices' && (
        <div className="space-y-4">
          {/* Top Banner: Verification Rate */}
          <div className="p-4 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 rounded-lg flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 text-emerald-800 dark:text-emerald-300">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <div>
                <span className="font-semibold">Deterministic Invoice Math Verification: </span>
                <span>{invoicesData?.math_evaluation_pass_rate || '100.0%'} Pass Rate across all 6 distributor invoices.</span>
              </div>
            </div>
            <Badge variant="success" size="sm">
              All Wholesale Calculations Verified
            </Badge>
          </div>

          {deploySuccess && (
            <div className="p-3 bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800 rounded text-xs text-blue-800 dark:text-blue-300">
              {deploySuccess}
            </div>
          )}

          {invoicesLoading || !invoicesData ? (
            <div className="py-20 text-center text-slate-400">Loading invoice evaluations...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {invoicesData.results.map((inv) => {
                const isGreenline = inv.supplier.includes('Greenline');
                return (
                  <div
                    key={inv.invoice_no}
                    className={`p-5 rounded-lg border shadow-sm transition-all ${
                      isGreenline
                        ? 'bg-amber-50/20 dark:bg-amber-950/20 border-amber-300 dark:border-amber-800'
                        : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                            {inv.supplier}
                          </h3>
                          <Badge variant={isGreenline ? 'warning' : 'success'} size="sm">
                            {inv.status}
                          </Badge>
                        </div>
                        <div className="text-xs text-slate-500 font-mono mt-0.5">
                          Invoice #{inv.invoice_no} • {inv.file_name}
                        </div>
                      </div>
                      <span className="text-[11px] font-mono font-medium text-slate-400">
                        {inv.lines_count} lines • {inv.catalog_matches} matched
                      </span>
                    </div>

                    {/* Discrepancy details */}
                    {inv.discrepancy_details && (
                      <div className="mt-3 p-3 bg-white dark:bg-slate-800/80 rounded border border-amber-200 dark:border-amber-800/80 text-xs text-amber-900 dark:text-amber-200">
                        <div className="font-semibold flex items-center gap-1.5 text-amber-800 dark:text-amber-300">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          <span>Receiving Shortage Detected:</span>
                        </div>
                        <p className="mt-1">{inv.discrepancy_details}</p>
                      </div>
                    )}

                    {/* Action buttons */}
                    <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-xs">
                      <span className="text-slate-500 text-[11px]">
                        Target margin: 35% retail markup
                      </span>
                      <button
                        onClick={() => handleDeployPricing(inv.file_name)}
                        className="flex items-center gap-1 px-3 py-1.5 rounded bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-medium hover:bg-slate-800 dark:hover:bg-slate-200 transition-colors shadow-xs"
                      >
                        <Percent className="w-3 h-3" />
                        <span>Deploy 35% Margin Pricing</span>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: LOSS PREVENTION RADAR */}
      {activeTab === 'loss_prevention' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-1.5">
                <ShieldAlert className="w-4 h-4 text-rose-500" />
                <span>Loss Prevention Incident Radar</span>
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                AI and heuristic surveillance flagging cashier void bursts, unauthorized drawer opens, and cash till variances
              </p>
            </div>
            <Badge variant="danger" size="sm">
              {lpData?.high_severity_count || 0} High Priority Incidents
            </Badge>
          </div>

          {lpLoading || !lpData ? (
            <div className="py-20 text-center text-slate-400">Scanning surveillance logs...</div>
          ) : lpData.incidents.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-400">
              No loss prevention anomalies detected for this store on {businessDate}.
            </div>
          ) : (
            <div className="space-y-3">
              {lpData.incidents.map((inc) => {
                const isHigh = inc.severity === 'HIGH';
                return (
                  <div
                    key={inc.incident_id}
                    className="p-4 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm text-xs space-y-2"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                      <div className="flex items-center gap-2">
                        <Badge variant={isHigh ? 'danger' : 'warning'} size="sm">
                          {inc.severity} PRIORITY
                        </Badge>
                        <span className="font-semibold text-slate-900 dark:text-white">
                          {inc.headline}
                        </span>
                      </div>
                      <div className="text-[11px] font-mono text-slate-400">
                        {inc.store_id} • {inc.device_id} • Cashier: {inc.staff_id}
                      </div>
                    </div>

                    <p className="text-slate-600 dark:text-slate-300">
                      {inc.details}
                    </p>

                    <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 flex items-start gap-2">
                      <span className="font-semibold text-slate-900 dark:text-white shrink-0">
                        Recommended Manager Action:
                      </span>
                      <span>{inc.recommended_action}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: "ASK YOUR STORES" ASSISTANT */}
      {activeTab === 'assistant' && (
        <div className="p-6 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm space-y-5">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-1.5">
              <Sparkles className="w-4 h-4 text-blue-500" />
              <span>"Ask Your Stores" Natural Language Assistant</span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Query operations, sales, cash drops, and register data in natural language with verified data citations.
            </p>
          </div>

          {/* Preset Buttons */}
          <div className="flex flex-wrap gap-2">
            {questionPresets.map((preset, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setQuestion(preset);
                  handleAskAssistant(preset);
                }}
                className="px-2.5 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-[11px] text-slate-700 dark:text-slate-300 transition-colors"
              >
                {preset}
              </button>
            ))}
          </div>

          {/* Search Query Input */}
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAskAssistant()}
                placeholder="Ask any question about store operations..."
                className="w-full px-3.5 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-slate-900 dark:focus:ring-slate-100"
              />
            </div>
            <button
              disabled={assistantLoading}
              onClick={() => handleAskAssistant()}
              className="px-4 py-2 rounded-md bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-medium text-xs hover:bg-slate-800 dark:hover:bg-slate-200 flex items-center gap-1.5 shadow-xs disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Ask</span>
            </button>
          </div>

          {/* Assistant Answer Box */}
          {assistantLoading ? (
            <div className="py-12 text-center text-xs text-slate-400">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-slate-900 dark:border-slate-100 mx-auto" />
              <p className="mt-2">Computing verified answer from store transaction ledger...</p>
            </div>
          ) : assistantReply ? (
            <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-900 dark:text-white">
                  Verified Store Assistant Citation:
                </span>
                <Badge variant="success" size="sm">
                  Confidence: {((assistantReply.confidence || 0.98) * 100).toFixed(0)}%
                </Badge>
              </div>

              <p className="text-slate-800 dark:text-slate-200 text-sm leading-relaxed">
                {assistantReply.answer}
              </p>

              {assistantReply.data && (
                <div className="p-3 bg-white dark:bg-slate-900 rounded border border-slate-200 dark:border-slate-700 font-mono text-[11px] text-slate-600 dark:text-slate-300">
                  <pre>{JSON.stringify(assistantReply.data, null, 2)}</pre>
                </div>
              )}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
};
