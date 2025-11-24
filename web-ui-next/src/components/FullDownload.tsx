"use client";

import { useState } from 'react';

interface FullDownloadProps {
  requestId: string | null;
}

export function FullDownload({ requestId }: FullDownloadProps) {
  const persist = true; // Always persist data
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('Awaiting plan...');

  const startFullRun = async () => {
    if (!requestId) {
      setStatus('No request ID found. Please plan first.');
      return;
    }

    setLoading(true);
    setStatus('Submitting full download job...');

    try {
      const res = await fetch('/api/start-full-run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          request_id: requestId,
          persist: persist
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        setStatus(data.detail || 'Failed to start full run.');
        return;
      }

      console.log('Full run started:', data);
      setStatus(`Full run submitted. Run ID: ${data.dagster_run_id}`);

    } catch (e: any) {
      setStatus('Error: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-6 rounded-3xl border border-white/10 bg-slate-950/60 p-6 backdrop-blur-xl">
        <h2 className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-amber-200 md:text-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(245,158,11,0.8)]" />
            Full Download
        </h2>
        <div className="mt-4 space-y-4">
            <div className="flex items-center gap-4">
                <button 
                    onClick={startFullRun}
                    disabled={!requestId || loading}
                    className="inline-flex items-center justify-center rounded-full bg-gradient-to-r from-amber-500 to-orange-500 px-5 py-2.5 text-sm font-bold text-white shadow-[0_0_20px_rgba(249,115,22,0.3)] transition-all hover:brightness-110 active:scale-95 disabled:opacity-50"
                >
                    {loading ? 'Submitting...' : 'Start Full Download'}
                </button>
                <p className="text-xs text-slate-400 font-mono truncate">{status}</p>
            </div>
        </div>
    </div>
  );
}
