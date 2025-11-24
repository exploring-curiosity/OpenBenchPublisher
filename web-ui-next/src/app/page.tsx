"use client";

import { useState, useEffect } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { ChatInterface } from '@/components/ChatInterface';
import { Dashboard } from '@/components/Dashboard';
import { OverviewPanel } from '@/components/OverviewPanel';
import { DatasetCard } from '@/components/DatasetCard';
import { RunHistory } from '@/components/RunHistory';
import { Database, Activity } from 'lucide-react';

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
  const [pendingDatasets, setPendingDatasets] = useState<Dataset[]>([]);
  const [activeView, setActiveView] = useState('overview');

  useEffect(() => {
    async function loadInitialData() {
      try {
        const res = await fetch("/api/datasets", { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          setDatasets(data.datasets || []);
          setPendingDatasets(data.pending_datasets || []);
        }
      } catch (error) {
        console.error('Failed to load datasets:', error);
      }
    }
    loadInitialData();
    
    // Refresh datasets every 30 seconds
    const interval = setInterval(loadInitialData, 30000);
    
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100">
      {/* VSCode-style Sidebar */}
      <Sidebar activeView={activeView} onViewChange={setActiveView} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <div className="h-12 bg-slate-900/50 border-b border-slate-800 flex items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <h1 className="text-sm font-semibold text-slate-200">
              {activeView === 'overview' && 'Overview'}
              {activeView === 'chat' && 'Chat Planner'}
              {activeView === 'build' && 'Build Tool'}
              {activeView === 'datasets' && 'Dataset Repository'}
              {activeView === 'runs' && 'Run History'}
            </h1>
            <div className="h-4 w-px bg-slate-700" />
            <span className="text-xs text-slate-500">DatasetSmith v1.0</span>
          </div>
          
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 px-2 py-1 bg-emerald-950/30 border border-emerald-800/30 rounded text-xs">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-emerald-300">Backend Online</span>
            </div>
            <div className="text-xs text-slate-500">localhost:8000</div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {activeView === 'overview' && <OverviewPanel datasets={datasets} />}
          
          {activeView === 'chat' && (
            <div className="h-full">
              <ChatInterface />
            </div>
          )}
          
          {activeView === 'build' && (
            <div className="h-full overflow-y-auto p-4">
              <Dashboard />
            </div>
          )}
          
          {activeView === 'datasets' && (
            <div className="h-full overflow-y-auto p-4">
              {/* Pending Datasets */}
              {pendingDatasets.length > 0 && (
                <div className="mb-6">
                  <h2 className="text-lg font-semibold text-amber-400 mb-3 flex items-center gap-2">
                    <Activity size={20} />
                    Pending Full Download ({pendingDatasets.length})
                  </h2>
                  <p className="text-xs text-slate-500 mb-3">These datasets have been sampled but not fully downloaded to your filesystem</p>
                  <div className="space-y-3">
                    {pendingDatasets.map((ds) => (
                      <DatasetCard 
                        key={ds._id} 
                        dataset={ds} 
                        formatDate={formatDate}
                        isPending={true}
                        onDelete={async () => {
                          const res = await fetch("/api/datasets", { cache: "no-store" });
                          if (res.ok) {
                            const data = await res.json();
                            setDatasets(data.datasets || []);
                            setPendingDatasets(data.pending_datasets || []);
                          }
                        }}
                      />
                    ))}
                  </div>
                </div>
              )}
              
              {/* Complete Datasets */}
              <div>
                <h2 className="text-lg font-semibold text-emerald-400 mb-3 flex items-center gap-2">
                  <Database size={20} />
                  Available Datasets ({datasets.length})
                </h2>
                <div className="space-y-3">
                  {datasets.length === 0 && pendingDatasets.length === 0 ? (
                    <div className="flex h-96 items-center justify-center border border-dashed border-slate-700 rounded-lg">
                      <div className="text-center">
                        <Database size={48} className="mx-auto mb-4 text-slate-600" />
                        <p className="text-sm text-slate-400">No datasets found</p>
                        <p className="text-xs text-slate-600 mt-2">Create your first dataset using Chat or Build Tool</p>
                      </div>
                    </div>
                  ) : datasets.length === 0 ? (
                    <div className="text-center py-8 text-slate-500 text-sm">
                      No fully downloaded datasets yet. Complete the pending downloads above.
                    </div>
                  ) : (
                    datasets.map((ds) => (
                      <DatasetCard 
                        key={ds._id} 
                        dataset={ds} 
                        formatDate={formatDate}
                        isPending={false}
                        onDelete={async () => {
                          const res = await fetch("/api/datasets", { cache: "no-store" });
                          if (res.ok) {
                            const data = await res.json();
                            setDatasets(data.datasets || []);
                            setPendingDatasets(data.pending_datasets || []);
                          }
                        }}
                      />
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
          
          {activeView === 'runs' && (
            <div className="p-6 h-full">
              <RunHistory />
            </div>
          )}

          {activeView === 'docs' && (
            <div className="p-6 max-w-4xl">
              <h2 className="text-2xl font-bold mb-6 text-slate-100">Documentation</h2>
              
              <div className="space-y-6 text-slate-300">
                <section>
                  <h3 className="text-xl font-semibold mb-3 text-cyan-400">Getting Started</h3>
                  <p className="mb-2">DatasetSmith helps you build, preview, and ship small multi-modal datasets.</p>
                  <ul className="list-disc list-inside space-y-1 ml-4">
                    <li>Use the <strong>Chat Planner</strong> to describe your dataset needs</li>
                    <li>Review and execute plans with one click</li>
                    <li>Monitor sampling progress in real-time</li>
                    <li>Download completed datasets as ZIP files</li>
                  </ul>
                </section>

                <section>
                  <h3 className="text-xl font-semibold mb-3 text-cyan-400">Chat Planner</h3>
                  <p className="mb-2">The Chat Planner uses GPT to help you design datasets:</p>
                  <ul className="list-disc list-inside space-y-1 ml-4">
                    <li>Describe your dataset in natural language</li>
                    <li>GPT extracts classes, data type, and sample count</li>
                    <li>Review the generated plan before execution</li>
                    <li>All conversations are saved with RAG-powered context</li>
                  </ul>
                </section>

                <section>
                  <h3 className="text-xl font-semibold mb-3 text-cyan-400">Build Tool</h3>
                  <p className="mb-2">Manual dataset creation interface:</p>
                  <ul className="list-disc list-inside space-y-1 ml-4">
                    <li>Plan: Define your dataset structure</li>
                    <li>Sample: Generate sample queries</li>
                    <li>Download: Export as ZIP (data persisted automatically)</li>
                  </ul>
                </section>

                <section>
                  <h3 className="text-xl font-semibold mb-3 text-cyan-400">Datasets</h3>
                  <p className="mb-2">View and manage your datasets:</p>
                  <ul className="list-disc list-inside space-y-1 ml-4">
                    <li>Preview samples before downloading</li>
                    <li>Download complete datasets</li>
                    <li>Re-download partially completed datasets</li>
                    <li>All data is persisted in MongoDB</li>
                  </ul>
                </section>

                <section>
                  <h3 className="text-xl font-semibold mb-3 text-cyan-400">Features</h3>
                  <ul className="list-disc list-inside space-y-1 ml-4">
                    <li><strong>RAG-Powered Chat:</strong> Context from past conversations using Voyage AI embeddings</li>
                    <li><strong>Real-time Progress:</strong> Watch sampling progress with live updates</li>
                    <li><strong>Persistent Storage:</strong> All data saved to MongoDB automatically</li>
                    <li><strong>Multi-modal Support:</strong> Images, text, and numerical data</li>
                    <li><strong>One-Click Download:</strong> Export datasets as organized ZIP files</li>
                  </ul>
                </section>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
