"use client";

import { ReactNode, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface CollapsibleSectionProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  badge?: string;
}

export function CollapsibleSection({ 
  title, 
  subtitle, 
  icon, 
  children, 
  defaultOpen = true,
  badge 
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="rounded-2xl border border-slate-800/50 bg-slate-900/30 backdrop-blur-sm overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-800/30 transition-colors"
      >
        <div className="flex items-center gap-4">
          {icon && <div className="text-cyan-400">{icon}</div>}
          <div className="text-left">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold text-slate-100">{title}</h2>
              {badge && (
                <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  {badge}
                </span>
              )}
            </div>
            {subtitle && <p className="text-sm text-slate-400 mt-1">{subtitle}</p>}
          </div>
        </div>
        <div className="text-slate-400">
          {isOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </div>
      </button>
      
      {isOpen && (
        <div className="px-6 py-4 border-t border-slate-800/50">
          {children}
        </div>
      )}
    </div>
  );
}
