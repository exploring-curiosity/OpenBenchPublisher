"use client";

import { useState, useEffect } from 'react';
import { Dashboard } from '@/components/Dashboard';
import { CollapsibleSection } from '@/components/CollapsibleSection';
import { Card3D } from '@/components/Card3D';
import { LayoutDashboard, Database, Workflow, Settings, BarChart3 } from 'lucide-react';

type Dataset = {
  _id: string;
  name: string;
  classes: string[];
  total_samples: number;
  created_at: string | null;
};

async function fetchDatasets(): Promise<Dataset[]> {
  try {
    const res = await fetch("/api/datasets", {
      cache: "no-store",
    });
    if (!res.ok) {
      return [];
    }
    const data = await res.json();
    return (data?.datasets as Dataset[]) ?? [];
  } catch {
    return [];
  }
}

function formatDate(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default function Home() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);

  useEffect(() => {
    async function loadInitialData() {
      const initialDatasets = await fetchDatasets();
      setDatasets(initialDatasets);
    }
    loadInitialData();
  }, []);

  const totalDatasets = datasets.length;
  const totalSamples = datasets.reduce(
    (acc, d) => acc + (Number(d.total_samples) || 0),
    0,
  );
  const classSet = new Set<string>();
  datasets.forEach((d) => (d.classes || []).forEach((c) => classSet.add(c)));

  return (
    <main className="min-h-screen">
      {/* Top Navigation Bar */}
      <nav className="sticky top-0 z-50 border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-xl">
        <div className="mx-auto max-w-[1600px] px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/20">
                <LayoutDashboard size={20} className="text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">DatasetSmith</h1>
                <p className="text-xs text-slate-400">Planning & Orchestration</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-950/30 px-3 py-1.5">
                <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-xs font-medium text-emerald-300">Backend Online</span>
              </div>
              <button className="rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700/50 transition-colors">
                <Settings size={16} className="inline mr-1" />
                Settings
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="mx-auto max-w-[1600px] px-6 py-8 space-y-6">
        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card3D>
            <div className="rounded-xl border border-slate-800/50 bg-gradient-to-br from-cyan-950/50 to-slate-900/50 p-6 backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Total Datasets</p>
                  <p className="mt-2 text-4xl font-bold text-white">{totalDatasets}</p>
                </div>
                <Database size={32} className="text-cyan-400 opacity-50" />
              </div>
            </div>
          </Card3D>
          
          <Card3D>
            <div className="rounded-xl border border-slate-800/50 bg-gradient-to-br from-blue-950/50 to-slate-900/50 p-6 backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Total Samples</p>
                  <p className="mt-2 text-4xl font-bold text-white">{totalSamples.toLocaleString()}</p>
                </div>
                <BarChart3 size={32} className="text-blue-400 opacity-50" />
              </div>
            </div>
          </Card3D>
          
          <Card3D>
            <div className="rounded-xl border border-slate-800/50 bg-gradient-to-br from-purple-950/50 to-slate-900/50 p-6 backdrop-blur-sm">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Unique Classes</p>
                  <p className="mt-2 text-4xl font-bold text-white">{classSet.size}</p>
                </div>
                <Workflow size={32} className="text-purple-400 opacity-50" />
              </div>
            </div>
          </Card3D>
        </div>

        {/* Planning Workflow */}
        <CollapsibleSection 
          title="Dataset Planning Workflow" 
          subtitle="Plan, preview, and execute dataset generation"
          icon={<Workflow size={24} />}
          badge="Active"
          defaultOpen={true}
        >
          <Dashboard />
        </CollapsibleSection>

        {/* Dataset Repository */}
        <CollapsibleSection 
          title="Dataset Repository" 
          subtitle="Browse and manage all generated datasets"
          icon={<Database size={24} />}
          badge={`${totalDatasets} datasets`}
          defaultOpen={true}
        >
          {datasets.length === 0 ? (
            <div className="flex h-40 items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-900/20 text-sm font-medium text-slate-500">
              No datasets found. Create your first dataset using the planning workflow above.
            </div>
          ) : (
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
              <div className="max-h-[460px] space-y-4 overflow-y-auto pr-2 text-sm scrollbar-thin scrollbar-track-transparent scrollbar-thumb-slate-800">
                {datasets.map((ds) => {
                  const classes = ds.classes || [];
                  const segments = classes.slice(0, 8);
                  const colors = [
                    "#22d3ee",
                    "#a855f7",
                    "#f97316",
                    "#4ade80",
                    "#38bdf8",
                    "#e11d48",
                  ];

                  return (
                    <Card3D key={ds._id}>
                      <article className="group relative overflow-hidden rounded-2xl border border-slate-800/50 bg-slate-900/40 px-5 py-4 transition-all duration-300 hover:border-cyan-500/40 hover:bg-slate-900/60 hover:shadow-[0_0_30px_rgba(34,211,238,0.1)]">
                        <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100" style={{ transform: 'skewX(-20deg) translateX(-150%)' }} />
                      
                      <div className="relative space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <h3 className="truncate font-mono text-sm font-medium text-slate-100 md:text-base group-hover:text-cyan-200 transition-colors">
                            {ds.name || "(unnamed dataset)"}
                          </h3>
                          <span className="rounded-full border border-white/10 bg-slate-950/50 px-2.5 py-0.5 text-[10px] font-bold font-mono text-cyan-300 shadow-[0_0_10px_rgba(34,211,238,0.2)]">
                            {ds.total_samples ?? 0} items
                          </span>
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-slate-400">
                          {classes.slice(0, 4).map((cls) => (
                            <span
                              key={cls}
                              className="rounded-md border border-white/5 bg-slate-800/50 px-2 py-0.5 text-[10px] font-medium text-slate-300"
                            >
                              {cls}
                            </span>
                          ))}
                          {classes.length > 4 && (
                            <span className="text-[11px] text-slate-500">
                              +{classes.length - 4} more
                            </span>
                          )}
                        </div>
                        {segments.length > 0 && (
                          <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-slate-800/50">
                            <div className="flex h-full w-full opacity-80 group-hover:opacity-100 transition-opacity">
                              {segments.map((cls, i) => (
                                <div
                                  key={cls + i}
                                  style={{
                                    backgroundColor: colors[i % colors.length],
                                    flex: 1,
                                  }}
                                  className="shadow-[0_0_10px_currentColor]"
                                />
                              ))}
                            </div>
                          </div>
                        )}
                        <div className="mt-1 flex items-center justify-between text-[11px] text-slate-400">
                          <span className="max-w-[60%] truncate font-mono text-[10px] text-slate-600 group-hover:text-slate-500 transition-colors">
                            {ds._id}
                          </span>
                          <span>{formatDate(ds.created_at)}</span>
                        </div>
                      </div>
                    </article>
                    </Card3D>
                  );
                })}
              </div>

              <div className="hidden max-h-[460px] overflow-y-auto rounded-2xl border border-white/5 bg-slate-900/20 text-xs text-slate-300 lg:block backdrop-blur-sm scrollbar-thin scrollbar-track-transparent scrollbar-thumb-slate-800">
                <table className="min-w-full border-collapse">
                  <thead className="sticky top-0 bg-slate-950/90 text-[10px] font-bold uppercase tracking-widest text-slate-500 backdrop-blur-md">
                    <tr>
                      <th className="px-4 py-3 text-left">Name</th>
                      <th className="px-4 py-3 text-left">Classes</th>
                      <th className="px-4 py-3 text-right">Total</th>
                      <th className="px-4 py-3 text-right">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {datasets.map((ds) => (
                      <tr
                        key={ds._id}
                        className="transition-colors hover:bg-white/5"
                      >
                        <td className="px-4 py-2.5 text-left font-medium text-slate-200">
                          {ds.name || "(unnamed dataset)"}
                        </td>
                        <td className="px-4 py-2.5 text-left text-slate-500">
                          {(ds.classes || []).join(", ")}
                        </td>
                        <td className="px-4 py-2.5 text-right font-mono text-cyan-300">
                          {ds.total_samples ?? 0}
                        </td>
                        <td className="px-4 py-2.5 text-right text-[10px] text-slate-500">
                          {formatDate(ds.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </CollapsibleSection>
      </div>
    </main>
  );
}
