"use client";

import { useState, useEffect } from 'react';
import { Clock, CheckCircle2, XCircle, Loader2, Download, Eye, Database, Image, FileText, BarChart2 } from 'lucide-react';

interface RunActivity {
  id: string;
  action: string;
  name: string;
  status: 'success' | 'running' | 'error' | 'pending';
  time: string;
  timestamp: string;
}

interface RunDetails {
  request_id: string;
  query: string;
  status: string;
  created_at: string;
  updated_at?: string;
  total_items?: number;
  downloaded?: number;
  classes?: string[];
  data_type?: string;
  error?: string;
}

export function RunHistory() {
  const [runs, setRuns] = useState<RunActivity[]>([]);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [runDetails, setRunDetails] = useState<RunDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);

  useEffect(() => {
    async function fetchRuns() {
      try {
        const res = await fetch('/api/runs');
        if (res.ok) {
          const data = await res.json();
          setRuns(data.runs || []);
        }
      } catch (error) {
        console.error('Failed to fetch runs:', error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchRuns();
    const interval = setInterval(fetchRuns, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchRunDetails = async (runId: string) => {
    setDetailsLoading(true);
    try {
      const res = await fetch(`/api/runs/${runId}`);
      if (res.ok) {
        const data = await res.json();
        setRunDetails(data);
      }
    } catch (error) {
      console.error('Failed to fetch run details:', error);
    } finally {
      setDetailsLoading(false);
    }
  };

  const handleRunClick = (runId: string) => {
    setSelectedRun(runId);
    fetchRunDetails(runId);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30';
      case 'running': return 'text-cyan-400 bg-cyan-400/10 border-cyan-400/30';
      case 'error': return 'text-red-400 bg-red-400/10 border-red-400/30';
      default: return 'text-slate-400 bg-slate-400/10 border-slate-400/30';
    }
  };

  const getDataTypeIcon = (type?: string) => {
    if (!type) return <Database size={16} />;
    const lower = type.toLowerCase();
    if (lower.includes('image')) return <Image size={16} />;
    if (lower.includes('text')) return <FileText size={16} />;
    if (lower.includes('numerical') || lower.includes('tabular')) return <BarChart2 size={16} />;
    return <Database size={16} />;
  };

  return (
    <div className="h-full flex gap-4">
      {/* Runs List */}
      <div className="w-1/2 flex flex-col">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-slate-200 flex items-center gap-2">
            <Clock size={20} />
            All Runs ({runs.length})
          </h3>
          <p className="text-xs text-slate-500 mt-1">Click on a run to view details</p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={32} className="animate-spin text-slate-600" />
          </div>
        ) : runs.length === 0 ? (
          <div className="flex-1 flex items-center justify-center border border-dashed border-slate-700 rounded-lg">
            <div className="text-center py-12">
              <Clock size={48} className="mx-auto mb-4 text-slate-600" />
              <p className="text-sm text-slate-400">No runs yet</p>
              <p className="text-xs text-slate-600 mt-2">Start building a dataset to see runs here</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto space-y-2">
            {runs.map(run => (
              <div
                key={run.id}
                onClick={() => handleRunClick(run.id)}
                className={`p-4 rounded-lg border cursor-pointer transition-all ${
                  selectedRun === run.id
                    ? 'bg-slate-800 border-cyan-500/50'
                    : 'bg-slate-900/50 border-slate-800 hover:border-slate-700 hover:bg-slate-800/50'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {run.status === 'success' && <CheckCircle2 size={18} className="text-emerald-400" />}
                    {run.status === 'running' && (
                      <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
                    )}
                    {run.status === 'error' && <XCircle size={18} className="text-red-400" />}
                    <span className={`text-xs px-2 py-0.5 rounded border ${getStatusColor(run.status)}`}>
                      {run.status}
                    </span>
                  </div>
                  <span className="text-xs text-slate-500">{run.time}</span>
                </div>
                <div className="text-sm font-medium text-slate-200 mb-1">{run.action}</div>
                <div className="text-xs text-slate-400 truncate">{run.name}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Run Details */}
      <div className="w-1/2 flex flex-col">
        {!selectedRun ? (
          <div className="flex-1 flex items-center justify-center border border-dashed border-slate-700 rounded-lg">
            <div className="text-center">
              <Eye size={48} className="mx-auto mb-4 text-slate-600" />
              <p className="text-sm text-slate-400">Select a run to view details</p>
            </div>
          </div>
        ) : detailsLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 size={32} className="animate-spin text-slate-600" />
          </div>
        ) : runDetails ? (
          <div className="flex-1 overflow-y-auto">
            <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                {getDataTypeIcon(runDetails.data_type)}
                Run Details
              </h3>

              <div className="space-y-4">
                {/* Request ID */}
                <div>
                  <label className="text-xs text-slate-500 uppercase font-semibold">Request ID</label>
                  <div className="mt-1 text-sm text-slate-300 font-mono bg-slate-950 p-2 rounded border border-slate-800 break-all">
                    {runDetails.request_id}
                  </div>
                </div>

                {/* Query */}
                <div>
                  <label className="text-xs text-slate-500 uppercase font-semibold">Query</label>
                  <div className="mt-1 text-sm text-slate-300 bg-slate-950 p-3 rounded border border-slate-800">
                    {runDetails.query}
                  </div>
                </div>

                {/* Status */}
                <div>
                  <label className="text-xs text-slate-500 uppercase font-semibold">Status</label>
                  <div className="mt-1">
                    <span className={`inline-flex items-center gap-2 text-sm px-3 py-1.5 rounded border ${getStatusColor(runDetails.status)}`}>
                      {runDetails.status === 'success' && <CheckCircle2 size={14} />}
                      {runDetails.status === 'running' && <Loader2 size={14} className="animate-spin" />}
                      {runDetails.status === 'error' && <XCircle size={14} />}
                      {runDetails.status}
                    </span>
                  </div>
                </div>

                {/* Progress */}
                {runDetails.total_items && (
                  <div>
                    <label className="text-xs text-slate-500 uppercase font-semibold">Progress</label>
                    <div className="mt-2">
                      <div className="flex justify-between text-sm text-slate-300 mb-1">
                        <span>{runDetails.downloaded || 0} / {runDetails.total_items}</span>
                        <span>{Math.round(((runDetails.downloaded || 0) / runDetails.total_items) * 100)}%</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-2">
                        <div
                          className="bg-gradient-to-r from-cyan-500 to-blue-500 h-2 rounded-full transition-all"
                          style={{ width: `${Math.min(((runDetails.downloaded || 0) / runDetails.total_items) * 100, 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Data Type */}
                {runDetails.data_type && (
                  <div>
                    <label className="text-xs text-slate-500 uppercase font-semibold">Data Type</label>
                    <div className="mt-1 text-sm text-slate-300 flex items-center gap-2">
                      {getDataTypeIcon(runDetails.data_type)}
                      {runDetails.data_type}
                    </div>
                  </div>
                )}

                {/* Classes */}
                {runDetails.classes && runDetails.classes.length > 0 && (
                  <div>
                    <label className="text-xs text-slate-500 uppercase font-semibold">Classes ({runDetails.classes.length})</label>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {runDetails.classes.map((cls, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-1 text-xs rounded bg-slate-800 text-slate-300 border border-slate-700"
                        >
                          {cls}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Timestamps */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-slate-500 uppercase font-semibold">Created</label>
                    <div className="mt-1 text-sm text-slate-300">
                      {new Date(runDetails.created_at).toLocaleString()}
                    </div>
                  </div>
                  {runDetails.updated_at && (
                    <div>
                      <label className="text-xs text-slate-500 uppercase font-semibold">Updated</label>
                      <div className="mt-1 text-sm text-slate-300">
                        {new Date(runDetails.updated_at).toLocaleString()}
                      </div>
                    </div>
                  )}
                </div>

                {/* Error */}
                {runDetails.error && (
                  <div>
                    <label className="text-xs text-slate-500 uppercase font-semibold">Error</label>
                    <div className="mt-1 text-sm text-red-400 bg-red-950/30 p-3 rounded border border-red-900/50">
                      {runDetails.error}
                    </div>
                  </div>
                )}

                {/* Actions */}
                {runDetails.status === 'success' && (
                  <div className="pt-4 border-t border-slate-800">
                    <button
                      onClick={() => window.open(`/download/${runDetails.request_id}`, '_blank')}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-lg hover:brightness-110 transition-all"
                    >
                      <Download size={16} />
                      Download Dataset
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center border border-dashed border-slate-700 rounded-lg">
            <div className="text-center">
              <XCircle size={48} className="mx-auto mb-4 text-slate-600" />
              <p className="text-sm text-slate-400">Failed to load run details</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
