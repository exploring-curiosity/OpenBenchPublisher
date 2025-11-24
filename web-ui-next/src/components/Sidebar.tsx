"use client";

import { useState } from 'react';
import { 
  LayoutDashboard, 
  MessageSquare, 
  Database, 
  Workflow, 
  Settings, 
  FileText,
  Activity
} from 'lucide-react';

interface SidebarProps {
  activeView: string;
  onViewChange: (view: string) => void;
}

export function Sidebar({ activeView, onViewChange }: SidebarProps) {
  const menuItems = [
    { id: 'overview', icon: LayoutDashboard, label: 'Overview' },
    { id: 'chat', icon: MessageSquare, label: 'Chat Planner' },
    { id: 'build', icon: Workflow, label: 'Build Tool' },
    { id: 'datasets', icon: Database, label: 'Datasets' },
    { id: 'runs', icon: Activity, label: 'Run History' },
    { id: 'docs', icon: FileText, label: 'Documentation' },
  ];

  return (
    <div className="w-16 bg-slate-950 border-r border-slate-800 flex flex-col items-center py-4 gap-2">
      {/* Logo */}
      <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600">
        <span className="text-white font-bold text-sm">DS</span>
      </div>

      {/* Menu Items */}
      {menuItems.map(item => (
        <button
          key={item.id}
          onClick={() => onViewChange(item.id)}
          className={`group relative flex h-12 w-12 items-center justify-center rounded-lg transition-colors ${
            activeView === item.id
              ? 'bg-slate-800 text-cyan-400'
              : 'text-slate-500 hover:bg-slate-800/50 hover:text-slate-300'
          }`}
          title={item.label}
        >
          <item.icon size={20} />
          
          {/* Tooltip */}
          <div className="absolute left-full ml-2 px-2 py-1 bg-slate-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50 border border-slate-700">
            {item.label}
          </div>

          {/* Active Indicator */}
          {activeView === item.id && (
            <div className="absolute left-0 w-1 h-8 bg-cyan-500 rounded-r" />
          )}
        </button>
      ))}

      {/* Settings at Bottom */}
      <div className="mt-auto">
        <button
          onClick={() => onViewChange('settings')}
          className={`flex h-12 w-12 items-center justify-center rounded-lg transition-colors ${
            activeView === 'settings'
              ? 'bg-slate-800 text-cyan-400'
              : 'text-slate-500 hover:bg-slate-800/50 hover:text-slate-300'
          }`}
          title="Settings"
        >
          <Settings size={20} />
        </button>
      </div>
    </div>
  );
}
