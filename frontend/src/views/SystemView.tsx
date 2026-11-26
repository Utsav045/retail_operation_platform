import React, { useEffect, useState } from 'react';
import {
  Server,
  ShieldAlert,
  FileCode,
  X,
  Copy,
  Check,
} from 'lucide-react';
import { api } from '../services/api';
import type { LiveStatusResponse, QuarantineItem } from '../types';
import { Badge } from '../components/common/Badge';

export const SystemView: React.FC = () => {
  const [liveStatus, setLiveStatus] = useState<LiveStatusResponse | null>(null);
  const [quarantineItems, setQuarantineItems] = useState<QuarantineItem[]>([]);
  const [, setLoading] = useState<boolean>(true);

  // Raw file modal
  const [inspectFile, setInspectFile] = useState<{ fileName: string; payload: string } | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    Promise.all([api.getLiveStatus(), api.getQuarantine()])
      .then(([statusRes, qRes]) => {
        setLiveStatus(statusRes);
        setQuarantineItems(qRes.items);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleOpenRawPayload = async (item: QuarantineItem) => {
    try {
      const res = await api.getQuarantinePayload(item.id);
      setInspectFile({ fileName: res.file_name, payload: res.payload });
    } catch {
      setInspectFile({ fileName: item.file_name, payload: item.payload_preview });
    }
  };

  const handleCopyPayload = () => {
    if (inspectFile?.payload) {
      navigator.clipboard.writeText(inspectFile.payload);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-white">
            System Integrity, Hub Health & Quarantine
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Monitor distributed store hub listeners, protocol formats, and inspect isolated corrupted transaction batches.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="success" size="sm">
            <span>Core Daemon Active</span>
          </Badge>
        </div>
      </div>

      {/* Store Nodes Ingestion Diagnostics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {liveStatus?.stores?.map((st) => (
          <div
            key={st.store_id}
            className="p-5 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm text-xs space-y-3"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-slate-500" />
                <h3 className="font-bold text-slate-900 dark:text-white text-sm">
                  {st.name} ({st.store_id})
                </h3>
              </div>
              <Badge variant="success" size="sm">
                ONLINE
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-2 font-mono text-[11px] pt-1 border-t border-slate-100 dark:border-slate-800">
              <div className="p-2 rounded bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                <span className="text-[10px] text-slate-400 block font-sans uppercase">Hub Location</span>
                <span className="font-semibold">{st.city}</span>
              </div>
              <div className="p-2 rounded bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                <span className="text-[10px] text-slate-400 block font-sans uppercase">TLOG Protocol</span>
                <span className="font-semibold text-blue-600 dark:text-blue-400">{st.format}</span>
              </div>
              <div className="p-2 rounded bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 col-span-2">
                <span className="text-[10px] text-slate-400 block font-sans uppercase">Total Batches Ingested</span>
                <span className="font-semibold">{st.batches_processed} batches</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quarantined Corrupt Batches Vault */}
      <div className="p-5 bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-500" />
              <span>Quarantined Transaction Batches Vault</span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Corrupted or unparseable batches safely isolated to preserve ground-truth ledger integrity
            </p>
          </div>
          <Badge variant="danger" size="sm">
            {quarantineItems.length} Files Quarantined
          </Badge>
        </div>

        {quarantineItems.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-400">
            No files currently in quarantine. Ingestion pipeline is clean.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400 font-medium">
                  <th className="py-2.5 px-3">Quarantined File</th>
                  <th className="py-2.5 px-3">Store</th>
                  <th className="py-2.5 px-3">Failure Reason</th>
                  <th className="py-2.5 px-3">Diagnostic Error Log</th>
                  <th className="py-2.5 px-3">Timestamp</th>
                  <th className="py-2.5 px-3 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {quarantineItems.map((q) => (
                  <tr key={q.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="py-2.5 px-3 font-mono font-medium text-slate-900 dark:text-white">
                      {q.file_name}
                    </td>
                    <td className="py-2.5 px-3 font-medium">{q.store_id}</td>
                    <td className="py-2.5 px-3">
                      <Badge variant="danger" size="sm">
                        {q.quarantine_reason}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 text-rose-600 dark:text-rose-400 max-w-xs truncate">
                      {q.error_details}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-400">
                      {new Date(q.quarantined_at).toLocaleString()}
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => handleOpenRawPayload(q)}
                        className="px-2.5 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium inline-flex items-center gap-1 text-[11px]"
                      >
                        <FileCode className="w-3.5 h-3.5 text-slate-500" />
                        <span>View Raw</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Raw Payload Modal */}
      {inspectFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="relative w-full max-w-3xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-2xl p-6 text-xs max-h-[90vh] overflow-y-auto space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-slate-500" />
                <h3 className="font-semibold text-slate-900 dark:text-white font-mono">
                  {inspectFile.fileName}
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyPayload}
                  className="flex items-center gap-1 px-2.5 py-1 rounded border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied!' : 'Copy'}</span>
                </button>
                <button
                  onClick={() => setInspectFile(null)}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 font-bold"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="p-4 bg-slate-950 text-slate-200 rounded-md font-mono text-[11px] overflow-x-auto max-h-96">
              <pre>{inspectFile.payload}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
