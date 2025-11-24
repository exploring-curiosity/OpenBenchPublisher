"use client";

import { useState } from 'react';

interface BuildFormProps {
  onPlanAndSample: (data: any) => void;
}

export function BuildForm({ onPlanAndSample }: BuildFormProps) {
  const [query, setQuery] = useState('');
  const [total, setTotal] = useState(50);
  const [type, setType] = useState('auto');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('Awaiting input...');

  const planAndSample = async () => {
    if (!query.trim()) {
      setStatus('Please enter a query.');
      return;
    }

    setLoading(true);
    setStatus('Planning and sampling via Dagster...');

    try {
      const res = await fetch('/api/plan-and-sample', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query: query,
          total_items: total,
          data_type: type 
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        setStatus(data.detail || 'Failed to run planner.');
        return;
      }

      onPlanAndSample(data);
      setStatus(`Planned ${data.plan.classes.length || 1} classes, sampled ${data.samples.length} items.`);

    } catch (e: any) {
      setStatus('Error: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="group relative overflow-hidden rounded-3xl border border-white/10 bg-slate-950/60 p-6 shadow-2xl backdrop-blur-xl transition-all duration-300 hover:border-cyan-500/30 hover:shadow-[0_0_40px_rgba(34,211,238,0.1)]">
        <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-fuchsia-500/5 opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
        <div className="flex items-center justify-between gap-3">
            <div>
                <h2 className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-cyan-100 md:text-sm">
                    <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)]" />
                    Build dataset
                </h2>
                <p className="mt-2 text-xs font-medium text-slate-400 md:text-sm">
                    Describe the dataset you want, choose a modality, and preview a sampled
                    plan before triggering a full Dagster run.
                </p>
            </div>
            <span className="rounded-full border border-amber-500/20 bg-amber-500/10 px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-amber-400 shadow-[0_0_15px_rgba(245,158,11,0.2)]">
                Step 1
            </span>
        </div>

        <div className="relative mt-6 space-y-5">
            <div>
                <label className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-slate-500">
                    Query
                </label>
                <input
                    type="text"
                    placeholder="e.g. 5-class image set: people, cars, books, dogs, mountains"
                    className="w-full rounded-lg border border-white/10 bg-slate-900/50 px-4 py-3 text-sm font-medium text-slate-200 placeholder-slate-600 shadow-inner backdrop-blur-sm transition-all hover:border-white/20 focus:border-cyan-500/50 focus:bg-slate-900/80 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    disabled={loading}
                />
            </div>
            <div className="grid grid-cols-2 gap-3">
                <div>
                    <label className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-slate-500">
                        Total items
                    </label>
                    <input
                        type="number"
                        value={total}
                        onChange={(e) => setTotal(parseInt(e.target.value, 10))}
                        className="w-full rounded-lg border border-white/10 bg-slate-900/50 px-4 py-3 text-sm font-mono font-medium text-slate-200 shadow-inner backdrop-blur-sm transition-all hover:border-white/20 focus:border-cyan-500/50 focus:bg-slate-900/80 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                        disabled={loading}
                    />
                </div>
                <div>
                    <label className="mb-2 block text-[10px] font-bold uppercase tracking-widest text-slate-500">
                        Data type
                    </label>
                    <select
                        value={type}
                        onChange={(e) => setType(e.target.value)}
                        className="w-full appearance-none rounded-lg border border-white/10 bg-slate-900/50 px-4 py-3 text-sm font-medium text-slate-200 shadow-inner backdrop-blur-sm transition-all hover:border-white/20 focus:border-fuchsia-500/50 focus:bg-slate-900/80 focus:outline-none focus:ring-2 focus:ring-fuchsia-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                        disabled={loading}
                    >
                        <option value="auto">Auto (planner decides)</option>
                        <option value="images">Images</option>
                        <option value="text">Text</option>
                        <option value="numerical">Numerical</option>
                    </select>
                </div>
            </div>
            <div className="flex items-center gap-4 pt-2">
                <button 
                    onClick={planAndSample}
                    disabled={loading}
                    className="inline-flex items-center justify-center rounded-full bg-gradient-to-r from-cyan-500 to-fuchsia-500 px-5 py-2.5 text-sm font-bold text-white shadow-[0_0_20px_rgba(59,130,246,0.3)] transition-all hover:brightness-110 active:scale-95 disabled:opacity-50"
                >
                    {loading ? 'Processing...' : 'Plan & Preview'}
                </button>
                <p className="text-xs text-slate-400 font-mono truncate">{status}</p>
            </div>
        </div>
    </div>
  );
}
