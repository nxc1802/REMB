'use client';

import React, { useState, useEffect, useCallback } from 'react';
import MapCanvas from '@/components/MapCanvas';
import ChatPanel from '@/components/ChatPanel';
import BlockList from '@/components/BlockList';
import api from '@/services/api';
import { BlockInfo, StateResponse, InfrastructureLine } from '@/types/api';

// Sample boundary for demo
const SAMPLE_BOUNDARY = [
  [0, 0], [200, 0], [200, 150], [0, 150], [0, 0]
];

const SAMPLE_ROADS = [
  {
    type: 'Feature',
    geometry: {
      type: 'LineString',
      coordinates: [[100, 0], [100, 150]]
    }
  }
];

export default function Home() {
  const [state, setState] = useState<StateResponse | null>(null);
  const [selectedBlock, setSelectedBlock] = useState<BlockInfo | null>(null);
  const [infrastructure, setInfrastructure] = useState<{
    electric_lines: InfrastructureLine[];
    water_lines: InfrastructureLine[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize with sample data
  const initializeSample = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.setBoundary(SAMPLE_BOUNDARY, SAMPLE_ROADS, 12);
      setState(response);
      setInfrastructure(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to initialize');
    } finally {
      setLoading(false);
    }
  };

  // Refresh state
  const refreshState = async () => {
    try {
      const response = await api.getState();
      setState(response);
    } catch (e) {
      console.error('Failed to refresh state:', e);
    }
  };

  // Handle chat message
  const handleChatSend = async (message: string): Promise<string> => {
    if (!selectedBlock) {
      return '⚠️ Vui lòng chọn một Block trước khi gửi yêu cầu.';
    }

    try {
      // Generate assets
      const genResult = await api.generateAssets({
        block_id: selectedBlock.id,
        user_request: message,
      });

      if (!genResult.success) {
        return `❌ Lỗi: ${genResult.error}`;
      }

      // Handle clear/replace actions
      if (genResult.action === 'clear' || genResult.action === 'replace') {
        await api.clearAssets(selectedBlock.id);
        await refreshState();

        // If clear action (no new assets to add), we're done
        if (genResult.action === 'clear') {
          return `🗑️ ${genResult.explanation}\n\n✅ Đã xóa tất cả assets khỏi ${selectedBlock.id}`;
        }
        // For replace action, continue to validate new assets
      }

      // Validate and merge new assets
      const valResult = await api.validateAssets({
        block_id: selectedBlock.id,
        new_assets: genResult.new_assets,
      });

      // Refresh state
      await refreshState();

      if (valResult.success) {
        const actionText = genResult.action === 'replace' ? 'Đã thay thế bằng' : 'Đã thêm';
        return `✅ ${genResult.explanation}\n\n📦 ${actionText} ${genResult.new_assets.length} assets vào ${selectedBlock.id}`;
      } else {
        return `⚠️ Không thể thêm assets:\n${valResult.errors.join('\n')}`;
      }
    } catch (e) {
      return `❌ Lỗi: ${e instanceof Error ? e.message : 'Unknown error'}`;
    }
  };

  // Handle finalize
  const handleFinalize = async () => {
    setLoading(true);
    try {
      const result = await api.finalize([0, 75], false);
      if (result.success) {
        setInfrastructure({
          electric_lines: result.electric_lines,
          water_lines: result.water_lines,
        });
      } else {
        setError(result.error || 'Finalize failed');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Finalize failed');
    } finally {
      setLoading(false);
    }
  };

  // Handle reset
  const handleReset = async () => {
    setLoading(true);
    try {
      await api.reset();
      setState(null);
      setSelectedBlock(null);
      setInfrastructure(null);
    } catch (e) {
      console.error('Reset failed:', e);
    } finally {
      setLoading(false);
    }
  };

  // Handle DXF upload
  const handleDxfUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setError(null);
    try {
      const response = await api.uploadDXF(file);
      setState(response);
      setInfrastructure(null);
      setSelectedBlock(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'DXF Upload failed');
    } finally {
      setLoading(false);
      // Reset input
      e.target.value = '';
    }
  };

  return (
    <main className="min-h-screen bg-gray-950 text-white p-6">
      {/* Header */}
      <header className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <span className="text-4xl">🏗️</span>
          SmartPlan AI v3.0
        </h1>
        <p className="text-gray-400 mt-1">
          Automated Industrial Park Planning Engine
        </p>
      </header>

      {/* Error banner */}
      {error && (
        <div className="mb-4 p-4 bg-red-900/50 border border-red-500 rounded-lg text-red-200">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-4 text-red-400 hover:text-red-200"
          >
            ✕
          </button>
        </div>
      )}

      {/* Action buttons */}
      <div className="mb-4 flex gap-2 items-center">
        <div className="relative">
          <label className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg cursor-pointer transition-colors block text-center min-w-[140px]">
            {loading ? 'Processing...' : '📂 Upload DXF'}
            <input
              type="file"
              accept=".dxf"
              onChange={handleDxfUpload}
              disabled={loading}
              className="hidden"
            />
          </label>
        </div>

        <button
          onClick={initializeSample}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50 transition-colors"
        >
          {loading ? 'Loading...' : '📥 Load Sample'}
        </button>

        {state && (
          <>
            <button
              onClick={handleFinalize}
              disabled={loading || !state.blocks.some(b => b.assets.length > 0)}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg disabled:opacity-50 transition-colors"
            >
              ⚡ Finalize Infrastructure
            </button>

            <button
              onClick={handleReset}
              disabled={loading}
              className="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg disabled:opacity-50 transition-colors"
            >
              🔄 Reset
            </button>
          </>
        )}
      </div>

      {/* Stats */}
      {state && (
        <div className="mb-4 grid grid-cols-4 gap-4">
          <div className="bg-gray-800 p-3 rounded-lg">
            <div className="text-2xl font-bold text-blue-400">
              {(state.total_area / 10000).toFixed(2)} ha
            </div>
            <div className="text-sm text-gray-400">Total Area</div>
          </div>
          <div className="bg-gray-800 p-3 rounded-lg">
            <div className="text-2xl font-bold text-green-400">
              {state.blocks.length}
            </div>
            <div className="text-sm text-gray-400">Blocks</div>
          </div>
          <div className="bg-gray-800 p-3 rounded-lg">
            <div className="text-2xl font-bold text-yellow-400">
              {(state.coverage_ratio * 100).toFixed(1)}%
            </div>
            <div className="text-sm text-gray-400">Coverage</div>
          </div>
          <div className="bg-gray-800 p-3 rounded-lg">
            <div className="text-2xl font-bold text-purple-400">
              {state.blocks.reduce((sum, b) => sum + b.assets.length, 0)}
            </div>
            <div className="text-sm text-gray-400">Assets</div>
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="grid grid-cols-12 gap-6">
        {/* Map */}
        <div className="col-span-8">
          <MapCanvas
            boundary={state?.boundary || null}
            blocks={state?.blocks || []}
            infrastructure={infrastructure || undefined}
            selectedBlockId={selectedBlock?.id}
            onBlockClick={setSelectedBlock}
            width={800}
            height={500}
          />
        </div>

        {/* Sidebar */}
        <div className="col-span-4 space-y-4">
          {/* Block List */}
          <BlockList
            blocks={state?.blocks || []}
            selectedBlockId={selectedBlock?.id}
            onBlockSelect={setSelectedBlock}
          />

          {/* Chat */}
          <ChatPanel
            onSend={handleChatSend}
            isLoading={loading}
            placeholder={selectedBlock
              ? `Yêu cầu cho ${selectedBlock.id}...`
              : 'Chọn block trước...'}
          />
        </div>
      </div>
    </main>
  );
}
