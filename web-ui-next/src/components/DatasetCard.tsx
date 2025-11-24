"use client";

import { useState, useEffect } from 'react';
import { Image, FileText, BarChart2, Database, Eye, Download, Trash2, AlertCircle } from 'lucide-react';

interface DatasetCardProps {
  dataset: {
    _id: string;
    name: string;
    classes: string[];
    total_samples: number;
    downloaded_samples?: number;
    created_at: string | null;
    data_type?: string;
  };
  formatDate: (date: string | null) => string;
  isPending?: boolean;
  onDelete?: () => void;
}

export function DatasetCard({ dataset, formatDate, isPending = false, onDelete }: DatasetCardProps) {
  const [preview, setPreview] = useState<any>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const classes = dataset.classes || [];
  const colors = ["#22d3ee", "#a855f7", "#f97316", "#4ade80", "#38bdf8", "#e11d48"];
  
  // Determine dataset type icon
  const getTypeIcon = () => {
    const type = dataset.data_type?.toLowerCase() || 'unknown';
    if (type.includes('image')) return <Image size={16} className="text-cyan-400" />;
    if (type.includes('text')) return <FileText size={16} className="text-purple-400" />;
    if (type.includes('numerical') || type.includes('tabular')) return <BarChart2 size={16} className="text-emerald-400" />;
    return <Database size={16} className="text-slate-400" />;
  };

  const fetchPreview = async () => {
    if (preview || loading) return;
    
    setLoading(true);
    try {
      const res = await fetch(`/api/datasets/${dataset._id}/preview`);
      if (res.ok) {
        const data = await res.json();
        setPreview(data);
      }
    } catch (error) {
      console.error('Failed to fetch preview:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderPreview = () => {
    if (loading) {
      return (
        <div className="grid grid-cols-3 gap-2 mt-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="aspect-square bg-slate-800 rounded animate-pulse" />
          ))}
        </div>
      );
    }

    if (!preview || !preview.samples) return null;

    const type = dataset.data_type?.toLowerCase() || '';
    
    if (type.includes('image')) {
      return (
        <div className="grid grid-cols-3 gap-2 mt-3">
          {preview.samples.slice(0, 6).map((sample: any, idx: number) => (
            <div key={idx} className="aspect-square bg-slate-800 rounded overflow-hidden border border-slate-700">
              {sample.url ? (
                <img 
                  src={sample.url} 
                  alt={sample.title || `Sample ${idx}`}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="100" height="100"%3E%3Crect fill="%23334155" width="100" height="100"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%2394a3b8" font-size="12"%3ENo Image%3C/text%3E%3C/svg%3E';
                  }}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-xs text-slate-500">
                  <Image size={20} />
                </div>
              )}
            </div>
          ))}
        </div>
      );
    }
    
    if (type.includes('text')) {
      return (
        <div className="mt-3 space-y-2">
          {preview.samples.slice(0, 3).map((sample: any, idx: number) => (
            <div key={idx} className="p-2 bg-slate-800 rounded border border-slate-700 text-xs text-slate-300 line-clamp-2">
              {sample.text || sample.content || 'No text content'}
            </div>
          ))}
        </div>
      );
    }

    // Default preview for other types
    return (
      <div className="mt-3 p-3 bg-slate-800 rounded border border-slate-700">
        <div className="text-xs text-slate-400">
          {preview.samples.length} samples available
        </div>
      </div>
    );
  };

  return (
    <div className="group relative overflow-hidden rounded-lg border border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:bg-slate-900/70 transition-all">
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              {getTypeIcon()}
              <h3 className="font-mono text-sm font-medium text-slate-100 group-hover:text-cyan-400 transition-colors">
                {dataset.name || "(unnamed dataset)"}
              </h3>
            </div>
            
            <div className="flex flex-wrap gap-1 mb-3">
              {classes.slice(0, 6).map((cls) => (
                <span
                  key={cls}
                  className="px-2 py-0.5 text-xs rounded bg-slate-800 text-slate-300 border border-slate-700"
                >
                  {cls}
                </span>
              ))}
              {classes.length > 6 && (
                <span className="px-2 py-0.5 text-xs text-slate-500">
                  +{classes.length - 6} more
                </span>
              )}
            </div>
          </div>
          
          <div className="text-right">
            <div className="text-lg font-bold text-cyan-400">{dataset.total_samples ?? 0}</div>
            <div className="text-xs text-slate-500">samples</div>
          </div>
        </div>
        
        {/* Action Buttons */}
        <div className="flex items-center gap-3 mb-3">
          <button
            onClick={() => {
              if (!showPreview) fetchPreview();
              setShowPreview(!showPreview);
            }}
            className="flex items-center gap-2 text-xs text-slate-400 hover:text-cyan-400 transition-colors"
          >
            <Eye size={14} />
            {showPreview ? 'Hide Preview' : 'Show Preview'}
          </button>
          
          {isPending ? (
            <button
              onClick={async () => {
                setDownloading(true);
                try {
                  const res = await fetch('/api/start-full-run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      request_id: dataset._id,
                      persist: true
                    })
                  });
                  if (res.ok) {
                    const data = await res.json();
                    alert(`✅ Full download started!\n\nRequest ID: ${data.request_id}\n\nThe dataset will be downloaded to your filesystem. Check the Datasets tab after completion.`);
                    if (onDelete) onDelete(); // Refresh the list
                  } else {
                    alert('❌ Failed to start full download. Please try again.');
                  }
                } catch (error) {
                  console.error('Failed to start full download:', error);
                  alert('❌ Error starting full download.');
                } finally {
                  setDownloading(false);
                }
              }}
              disabled={downloading}
              className="flex items-center gap-2 px-3 py-1 bg-amber-600 hover:bg-amber-500 disabled:bg-amber-800 disabled:cursor-not-allowed text-white text-xs rounded transition-colors"
            >
              <Download size={14} />
              {downloading ? 'Starting...' : 'Start Full Download'}
            </button>
          ) : (
            <button
              onClick={() => window.open(`/download/${dataset._id}`, '_blank')}
              className="flex items-center gap-2 text-xs text-slate-400 hover:text-emerald-400 transition-colors"
            >
              <Download size={14} />
              Download ZIP
            </button>
          )}
          
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="flex items-center gap-2 text-xs text-slate-400 hover:text-red-400 transition-colors ml-auto"
          >
            <Trash2 size={14} />
            Delete
          </button>
        </div>
        
        {/* Delete Confirmation */}
        {showDeleteConfirm && (
          <div className="mb-3 p-3 bg-red-950/30 border border-red-800/50 rounded-lg">
            <div className="flex items-start gap-2 mb-2">
              <AlertCircle size={16} className="text-red-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm text-red-300 font-medium mb-1">Delete Dataset?</p>
                <p className="text-xs text-red-400/80">
                  {isPending 
                    ? 'This will delete the sampled dataset. You can recreate it anytime.'
                    : 'This will permanently delete all downloaded files and metadata.'}
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={async () => {
                  setDeleting(true);
                  try {
                    const res = await fetch(`/api/datasets/${dataset._id}`, {
                      method: 'DELETE',
                    });
                    if (res.ok && onDelete) {
                      onDelete();
                    }
                  } catch (error) {
                    console.error('Failed to delete dataset:', error);
                  } finally {
                    setDeleting(false);
                    setShowDeleteConfirm(false);
                  }
                }}
                disabled={deleting}
                className="flex-1 px-3 py-1.5 bg-red-600 hover:bg-red-500 disabled:bg-red-800 disabled:cursor-not-allowed text-white text-xs rounded transition-colors"
              >
                {deleting ? 'Deleting...' : 'Yes, Delete'}
              </button>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleting}
                className="flex-1 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 text-slate-300 text-xs rounded transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Preview Content */}
        {showPreview && renderPreview()}
        
        {/* Color Bar */}
        {classes.length > 0 && (
          <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-slate-800">
            <div className="flex h-full w-full">
              {classes.slice(0, 6).map((cls, i) => (
                <div
                  key={cls + i}
                  style={{
                    backgroundColor: colors[i % colors.length],
                    flex: 1,
                  }}
                />
              ))}
            </div>
          </div>
        )}
        
        {/* Footer */}
        <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
          <span className="font-mono truncate max-w-[60%]">{dataset._id}</span>
          <span>{formatDate(dataset.created_at)}</span>
        </div>
      </div>
    </div>
  );
}
