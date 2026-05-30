import React, { useState } from 'react';
import { FloatingOverlay } from './components/overlay/FloatingOverlay';
import { WorkspaceDashboard } from './components/dashboard/WorkspaceDashboard';

const App: React.FC = () => {
  const [viewMode, setViewMode] = useState<'dashboard' | 'overlay'>('dashboard');

  return (
    <div className="relative min-h-screen bg-[#09090b] text-white">
      {/* Absolute toggle float for quick view switching */}
      <div className="fixed bottom-4 right-4 z-50 bg-[#121216]/90 border border-purple-500/20 px-3 py-2 rounded-2xl shadow-xl flex items-center space-x-2 backdrop-blur-md">
        <span className="text-[10px] text-gray-400 font-semibold tracking-wider uppercase">Active View:</span>
        <button
          onClick={() => setViewMode('dashboard')}
          className={`px-3 py-1.5 rounded-xl text-[10px] font-bold uppercase transition-all ${
            viewMode === 'dashboard'
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/20'
              : 'text-gray-400 hover:bg-white/5'
          }`}
        >
          Workspace
        </button>
        <button
          onClick={() => setViewMode('overlay')}
          className={`px-3 py-1.5 rounded-xl text-[10px] font-bold uppercase transition-all ${
            viewMode === 'overlay'
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/20'
              : 'text-gray-400 hover:bg-white/5'
          }`}
        >
          Copilot Widget
        </button>
      </div>

      {/* Renders Selected View Mode */}
      {viewMode === 'dashboard' ? (
        <WorkspaceDashboard />
      ) : (
        <div className="min-h-screen flex items-center justify-center p-8 bg-black/40">
          <FloatingOverlay />
        </div>
      )}
    </div>
  );
};

export default App;
