'use client';

import { useState } from 'react';
import { SelectedElement } from '@/types';

interface ControlPanelProps {
    selectedElement: SelectedElement | null;
    onApplyTemplate: (template: string, cellSize: number, rotation: number) => void;
    onSubdivide: (lotSize: number) => void;
    onReset: () => void;
    onLoadSample: () => void;
    onUploadDXF: (file: File) => void;
    stats: {
        roadCount: number;
        blockCount: number;
        lotCount: number;
    };
}

const TEMPLATES = [
    { id: 'spine', name: 'Trục Trung Tâm', icon: '🦴', desc: 'Đường chính giữa' },
    { id: 'grid', name: 'Bàn Cờ', icon: '🔲', desc: 'Lưới vuông góc' },
    { id: 'loop', name: 'Vành Đai', icon: '⭕', desc: 'Đường vòng quanh' },
    { id: 'cross', name: 'Chữ Thập', icon: '✚', desc: 'Hai trục cắt nhau' },
];

export default function ControlPanel({
    selectedElement,
    onApplyTemplate,
    onSubdivide,
    onReset,
    onLoadSample,
    onUploadDXF,
    stats,
}: ControlPanelProps) {
    const [cellSize, setCellSize] = useState(100);
    const [rotation, setRotation] = useState(0);
    const [activeTemplate, setActiveTemplate] = useState<string | null>(null);

    const handleTemplateClick = (templateId: string) => {
        setActiveTemplate(templateId);
        onApplyTemplate(templateId, cellSize, rotation);
    };

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            onUploadDXF(file);
        }
        e.target.value = '';
    };

    return (
        <div className="space-y-5 overflow-y-auto h-full pr-2">
            {/* Stats Bar */}
            <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-1.5">
                    <span className="text-xl font-bold text-indigo-400">{stats.roadCount}</span>
                    <span className="text-slate-500">Đường</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <span className="text-xl font-bold text-purple-400">{stats.blockCount}</span>
                    <span className="text-slate-500">Block</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <span className="text-xl font-bold text-emerald-400">{stats.lotCount}</span>
                    <span className="text-slate-500">Lô</span>
                </div>
            </div>

            {/* Selected Element */}
            {selectedElement && (
                <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                    <div className="flex items-center gap-2 text-amber-400">
                        <span className="text-lg">🎯</span>
                        <span className="font-medium">{selectedElement.name}</span>
                        <span className="text-xs text-amber-500/70">({selectedElement.type})</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                        Chat: &ldquo;Xóa {selectedElement.name}&rdquo; hoặc &ldquo;Di chuyển {selectedElement.name} 50m&rdquo;
                    </p>
                </div>
            )}

            {/* Boundary Section */}
            <div className="space-y-2">
                <h3 className="text-sm font-semibold text-slate-400 flex items-center gap-2">
                    📍 Ranh giới
                </h3>
                <div className="flex gap-2">
                    <button
                        onClick={onLoadSample}
                        className="flex-1 px-3 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg text-sm font-medium hover:from-indigo-500 hover:to-purple-500 transition-all"
                    >
                        Mẫu 500×400m
                    </button>
                    <label className="flex-1">
                        <div className="px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-center cursor-pointer hover:bg-slate-700 transition-colors">
                            📁 Tải DXF
                        </div>
                        <input
                            type="file"
                            accept=".dxf"
                            onChange={handleFileUpload}
                            className="hidden"
                        />
                    </label>
                </div>
            </div>

            {/* Templates */}
            <div className="space-y-2">
                <h3 className="text-sm font-semibold text-slate-400 flex items-center gap-2">
                    🛣️ Templates
                </h3>
                <div className="grid grid-cols-2 gap-2">
                    {TEMPLATES.map((t) => (
                        <button
                            key={t.id}
                            onClick={() => handleTemplateClick(t.id)}
                            className={`flex flex-col items-center p-3 rounded-lg border transition-all ${activeTemplate === t.id
                                    ? 'bg-indigo-600/20 border-indigo-500'
                                    : 'bg-slate-700/30 border-slate-600/50 hover:border-slate-500'
                                }`}
                        >
                            <span className="text-2xl mb-1">{t.icon}</span>
                            <span className="text-xs font-medium">{t.name}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Parameters */}
            <div className="space-y-3">
                <h3 className="text-sm font-semibold text-slate-400 flex items-center gap-2">
                    ⚙️ Tham số
                </h3>

                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-400">Kích thước ô</span>
                        <span className="text-sm font-mono text-indigo-400">{cellSize}m</span>
                    </div>
                    <input
                        type="range"
                        min={50}
                        max={200}
                        value={cellSize}
                        onChange={(e) => setCellSize(parseInt(e.target.value))}
                        className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />
                </div>

                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-slate-400">Góc xoay</span>
                        <span className="text-sm font-mono text-indigo-400">{rotation}°</span>
                    </div>
                    <input
                        type="range"
                        min={-45}
                        max={45}
                        value={rotation}
                        onChange={(e) => setRotation(parseInt(e.target.value))}
                        className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />
                </div>

                <button
                    onClick={() => activeTemplate && onApplyTemplate(activeTemplate, cellSize, rotation)}
                    className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm hover:bg-slate-700 transition-colors"
                >
                    ♻️ Áp dụng lại
                </button>
            </div>

            {/* Actions */}
            <div className="space-y-2">
                <h3 className="text-sm font-semibold text-slate-400 flex items-center gap-2">
                    🎯 Hành động
                </h3>
                <button
                    onClick={() => onSubdivide(2000)}
                    className="w-full px-3 py-2 bg-emerald-600/20 border border-emerald-600/50 rounded-lg text-sm text-emerald-400 hover:bg-emerald-600/30 transition-colors"
                >
                    📐 Chia lô tự động
                </button>
                <button
                    onClick={onReset}
                    className="w-full px-3 py-2 bg-rose-600/10 border border-rose-600/30 rounded-lg text-sm text-rose-400 hover:bg-rose-600/20 transition-colors"
                >
                    🔄 Reset thiết kế
                </button>
            </div>
        </div>
    );
}
