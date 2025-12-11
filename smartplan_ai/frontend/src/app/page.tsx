'use client';

import { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import ControlPanel from '@/components/ControlPanel';
import ChatPanel from '@/components/ChatPanel';
import { FeatureCollection, SelectedElement, ChatMessage, ChatResponse } from '@/types';
import * as api from '@/services/api';

// Dynamic import for canvas (no SSR)
const MapCanvas = dynamic(() => import('@/components/MapCanvas'), { ssr: false });

export default function Home() {
  const [sessionId] = useState(() => `web-${Date.now()}`);
  const [designState, setDesignState] = useState<FeatureCollection | null>(null);
  const [selectedElement, setSelectedElement] = useState<SelectedElement | null>(null);
  const [selectedElements, setSelectedElements] = useState<SelectedElement[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'Xin chào! Tôi là trợ lý thiết kế quy hoạch khu công nghiệp. Hãy tải ranh giới và chọn template để bắt đầu!',
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [stats, setStats] = useState({ roadCount: 0, blockCount: 0, lotCount: 0 });

  const updateStats = useCallback((state: FeatureCollection | null) => {
    if (!state?.features) {
      setStats({ roadCount: 0, blockCount: 0, lotCount: 0 });
      return;
    }
    setStats({
      roadCount: state.features.filter((f) => f.properties?.type === 'road').length,
      blockCount: state.features.filter((f) => f.properties?.type === 'block').length,
      lotCount: state.features.filter((f) => f.properties?.type === 'lot').length,
    });
  }, []);

  const handleLoadSample = async () => {
    const boundary = {
      type: 'Polygon',
      coordinates: [[[0, 0], [500, 0], [500, 400], [0, 400], [0, 0]]],
    };

    const result = await api.setBoundary(boundary, sessionId);
    if (result) {
      addMessage('assistant', '✅ Đã tải mẫu 500×400m. Chọn template để bắt đầu thiết kế!');
    }
  };

  const handleUploadDXF = async (file: File) => {
    const result = await api.uploadDXF(file);
    if (result?.success && result.boundaries?.features?.[0]) {
      const boundary = result.boundaries.features[0].geometry;
      await api.setBoundary(boundary, sessionId);
      addMessage('assistant', `✅ Đã tải ${file.name}. Chọn template để bắt đầu thiết kế!`);
    } else {
      addMessage('assistant', '❌ Không tìm thấy boundary trong DXF');
    }
  };

  const handleApplyTemplate = async (template: string, cellSize: number, rotation: number) => {
    setIsLoading(true);
    const result = await api.applyTemplate(template, cellSize, rotation, sessionId) as {
      success: boolean;
      state: FeatureCollection;
      message: string;
    } | null;

    if (result?.success) {
      setDesignState(result.state);
      updateStats(result.state);
      addMessage('assistant', `✅ ${result.message}`);
    }
    setIsLoading(false);
  };

  const handleSubdivide = async (lotSize: number) => {
    setIsLoading(true);
    const result = await api.subdivideBlocks(lotSize, sessionId) as {
      success: boolean;
      state: FeatureCollection;
      message: string;
    } | null;

    if (result?.success) {
      setDesignState(result.state);
      updateStats(result.state);
      addMessage('assistant', `✅ ${result.message}`);
    }
    setIsLoading(false);
  };

  const handleReset = async () => {
    setDesignState(null);
    setSelectedElement(null);
    setSelectedElements([]);
    setStats({ roadCount: 0, blockCount: 0, lotCount: 0 });
    setMessages([{
      role: 'assistant',
      content: '🔄 Đã reset thiết kế. Tải ranh giới mới để bắt đầu lại.',
    }]);
  };

  const handleSendMessage = async (message: string) => {
    addMessage('user', message);
    setIsLoading(true);

    // Send primary selection or first of multi-selection
    const elementToSend = selectedElement || (selectedElements.length > 0 ? selectedElements[0] : null);
    const result = await api.sendChatMessage(message, sessionId, elementToSend) as ChatResponse | null;

    if (result) {
      addMessage('assistant', result.text || 'Không có phản hồi');

      if (result.state) {
        setDesignState(result.state);
        updateStats(result.state);
      }

      if (result.action_result?.success) {
        if (result.action_result.message?.includes('chuyển') ||
          result.action_result.message?.includes('xóa')) {
          setSelectedElement(null);
          setSelectedElements([]);
        }
      }
    }

    setIsLoading(false);
  };

  const addMessage = (role: 'user' | 'assistant', content: string) => {
    setMessages((prev) => [...prev, { role, content }]);
  };

  const handleSelectElement = (element: SelectedElement | null, isMulti: boolean = false) => {
    if (!element) {
      // Click on empty area - clear all selections
      setSelectedElement(null);
      setSelectedElements([]);
      return;
    }

    if (isMulti) {
      // Shift+click - toggle in multi-selection array
      setSelectedElements(prev => {
        const exists = prev.some(e => e.name === element.name);
        if (exists) {
          // Remove from selection
          return prev.filter(e => e.name !== element.name);
        } else {
          // Add to selection
          return [...prev, element];
        }
      });
      // Also set as primary if no primary selected
      if (!selectedElement) {
        setSelectedElement(element);
      }
    } else {
      // Normal click - single selection, clear multi
      setSelectedElement(element);
      setSelectedElements([element]);
    }
    console.log('Selected:', element, 'Multi:', isMulti);
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col">
      {/* Header */}
      <header className="py-4 px-6 border-b border-slate-700/50 bg-slate-800/50 backdrop-blur">
        <div className="flex items-center justify-between max-w-[1800px] mx-auto">
          <div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
              🏗️ SmartPlan AI
            </h1>
            <p className="text-sm text-slate-400">Design by Conversation</p>
          </div>
          <div className="flex items-center gap-4">
            <button className="px-4 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm hover:bg-slate-700 transition-colors">
              📄 Export GeoJSON
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex max-w-[1800px] mx-auto w-full p-4 gap-4">
        {/* Map Panel */}
        <section className="flex-[2] bg-slate-800/30 rounded-xl border border-slate-700/50 p-4 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-slate-300">🗺️ Bản đồ thiết kế</h2>
            <div className="flex items-center gap-4 text-sm">
              <span className="text-slate-500">
                {selectedElements.length > 1 ? (
                  <span className="text-amber-400">🎯 {selectedElements.length} selected (Shift+click)</span>
                ) : selectedElement ? (
                  <span className="text-amber-400">🎯 {selectedElement.name}</span>
                ) : (
                  'Click để chọn (Shift+click để chọn nhiều)'
                )}
              </span>
            </div>
          </div>
          <div className="flex-1 min-h-[500px]">
            <MapCanvas
              designState={designState}
              selectedElement={selectedElement}
              selectedElements={selectedElements}
              onSelectElement={handleSelectElement}
              showLabels={true}
            />
          </div>
        </section>

        {/* Right Sidebar */}
        <aside className="w-[380px] flex flex-col gap-4">
          {/* Control Panel */}
          <section className="bg-slate-800/30 rounded-xl border border-slate-700/50 p-4 flex-1 min-h-0">
            <ControlPanel
              selectedElement={selectedElement}
              onApplyTemplate={handleApplyTemplate}
              onSubdivide={handleSubdivide}
              onReset={handleReset}
              onLoadSample={handleLoadSample}
              onUploadDXF={handleUploadDXF}
              stats={stats}
            />
          </section>

          {/* Chat Panel */}
          <section className="bg-slate-800/30 rounded-xl border border-slate-700/50 p-4 h-[400px]">
            <ChatPanel
              messages={messages}
              selectedElement={selectedElement}
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
            />
          </section>
        </aside>
      </main>
    </div>
  );
}
