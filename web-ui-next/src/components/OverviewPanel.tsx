"use client";

import { useState, useEffect } from 'react';
import { Database, BarChart3, Workflow, Clock, CheckCircle2, XCircle, Loader2 } from 'lucide-react';

interface OverviewPanelProps {
  datasets: any[];
}

interface RunActivity {
  id: string;
  action: string;
  name: string;
  status: 'success' | 'running' | 'error' | 'pending';
  time: string;
  timestamp: string;
}

export function OverviewPanel({ datasets }: OverviewPanelProps) {
  const [recentActivity, setRecentActivity] = useState<RunActivity[]>([]);
  const [loading, setLoading] = useState(true);

  const totalSamples = datasets.reduce((acc, d) => acc + (Number(d.total_samples) || 0), 0);
  const classSet = new Set<string>();
  datasets.forEach((d) => (d.classes || []).forEach((c: string) => classSet.add(c)));

  useEffect(() => {
    async function fetchActivity() {
      try {
        const res = await fetch('/api/runs');
        if (res.ok) {
          const data = await res.json();
          setRecentActivity(data.runs || []);
        }
      } catch (error) {
        console.error('Failed to fetch activity:', error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchActivity();
    // Poll every 10 seconds
    const interval = setInterval(fetchActivity, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-full overflow-y-auto">
      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-3 p-4 bg-slate-900/30">
        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-400 uppercase font-semibold">Datasets</span>
            <Database size={16} className="text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white">{datasets.length}</div>
        </div>

        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-400 uppercase font-semibold">Samples</span>
            <BarChart3 size={16} className="text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white">{totalSamples.toLocaleString()}</div>
        </div>

        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-400 uppercase font-semibold">Classes</span>
            <Workflow size={16} className="text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white">{classSet.size}</div>
        </div>

        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-400 uppercase font-semibold">Active Runs</span>
            <Clock size={16} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white">0</div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="p-4">
        <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
          <Clock size={16} />
          Recent Activity
        </h3>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={24} className="animate-spin text-slate-600" />
          </div>
        ) : recentActivity.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            No recent activity. Start building a dataset to see activity here.
          </div>
        ) : (
          <div className="space-y-2">
            {recentActivity.map(activity => (
            <div
              key={activity.id}
              className="flex items-center justify-between p-3 bg-slate-900/50 border border-slate-800 rounded-lg hover:border-slate-700 transition-colors"
            >
              <div className="flex items-center gap-3">
                {activity.status === 'success' && <CheckCircle2 size={16} className="text-emerald-400" />}
                {activity.status === 'running' && (
                  <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
                )}
                {activity.status === 'error' && <XCircle size={16} className="text-red-400" />}
                <div>
                  <div className="text-sm text-slate-200">{activity.action}</div>
                  <div className="text-xs text-slate-500">{activity.name}</div>
                </div>
              </div>
              <span className="text-xs text-slate-500">{activity.time}</span>
            </div>
          ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="p-4">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Quick Actions</h3>
        <div className="grid grid-cols-2 gap-2">
          <button className="p-3 bg-cyan-600/20 border border-cyan-600/30 rounded-lg text-left hover:bg-cyan-600/30 transition-colors">
            <div className="text-sm font-medium text-cyan-400">New Dataset</div>
            <div className="text-xs text-slate-400 mt-1">Start planning</div>
          </button>
          <button className="p-3 bg-blue-600/20 border border-blue-600/30 rounded-lg text-left hover:bg-blue-600/30 transition-colors">
            <div className="text-sm font-medium text-blue-400">View Runs</div>
            <div className="text-xs text-slate-400 mt-1">Check status</div>
          </button>
          <button className="p-3 bg-purple-600/20 border border-purple-600/30 rounded-lg text-left hover:bg-purple-600/30 transition-colors">
            <div className="text-sm font-medium text-purple-400">Browse Data</div>
            <div className="text-xs text-slate-400 mt-1">Explore datasets</div>
          </button>
          <button className="p-3 bg-emerald-600/20 border border-emerald-600/30 rounded-lg text-left hover:bg-emerald-600/30 transition-colors">
            <div className="text-sm font-medium text-emerald-400">Documentation</div>
            <div className="text-xs text-slate-400 mt-1">Learn more</div>
          </button>
        </div>
      </div>
    </div>
  );
}
