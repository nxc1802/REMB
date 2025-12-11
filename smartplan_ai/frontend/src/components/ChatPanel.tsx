'use client';

import { useState, useRef, useEffect } from 'react';
import { ChatMessage, SelectedElement } from '@/types';

interface ChatPanelProps {
    messages: ChatMessage[];
    selectedElement: SelectedElement | null;
    onSendMessage: (message: string) => void;
    isLoading?: boolean;
}

const QUICK_ACTIONS = [
    { label: '🔲 Bàn cờ', message: 'Tạo lưới bàn cờ' },
    { label: '🦴 Trục chính', message: 'Tạo lưới trục trung tâm' },
    { label: '↔️ Rộng hơn', message: 'Làm đường rộng hơn 30m' },
    { label: '🔄 Xoay 15°', message: 'Xoay 15 độ' },
    { label: '📐 Chia lô', message: 'Chia lô tự động' },
];

export default function ChatPanel({
    messages,
    selectedElement,
    onSendMessage,
    isLoading = false,
}: ChatPanelProps) {
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (input.trim() && !isLoading) {
            onSendMessage(input.trim());
            setInput('');
        }
    };

    const placeholder = selectedElement
        ? `Đang chọn ${selectedElement.name}. VD: "Xóa ${selectedElement.name}" hoặc "Di chuyển ${selectedElement.name} 50m"`
        : 'Nhập lệnh (VD: Tạo lưới bàn cờ)';

    return (
        <div className="flex flex-col h-full">
            <h3 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2">
                💬 Trò chuyện với AI
            </h3>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-3 min-h-0 mb-3 pr-2">
                {messages.map((msg, i) => (
                    <div
                        key={i}
                        className={`p-3 rounded-lg text-sm ${msg.role === 'user'
                                ? 'bg-indigo-600/30 ml-8 text-slate-200'
                                : 'bg-slate-700/50 mr-4 text-slate-300'
                            }`}
                    >
                        <span className="text-xs font-medium text-slate-500 block mb-1">
                            {msg.role === 'user' ? 'Bạn' : 'AI'}
                        </span>
                        {msg.content}
                    </div>
                ))}
                {isLoading && (
                    <div className="bg-slate-700/50 mr-4 p-3 rounded-lg">
                        <div className="flex items-center gap-2 text-slate-400">
                            <div className="animate-pulse">●</div>
                            <span className="text-sm">Đang xử lý...</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="flex gap-2">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={placeholder}
                    disabled={isLoading}
                    className="flex-1 px-4 py-2.5 bg-slate-700/50 border border-slate-600 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors disabled:opacity-50"
                />
                <button
                    type="submit"
                    disabled={isLoading || !input.trim()}
                    className="px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 rounded-lg font-medium text-sm hover:from-indigo-500 hover:to-purple-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Gửi
                </button>
            </form>

            {/* Quick Actions */}
            <div className="flex flex-wrap gap-2 mt-3">
                {QUICK_ACTIONS.map((action) => (
                    <button
                        key={action.message}
                        onClick={() => onSendMessage(action.message)}
                        disabled={isLoading}
                        className="px-3 py-1.5 bg-slate-700/50 border border-slate-600 rounded-md text-xs text-slate-400 hover:text-white hover:border-slate-500 transition-colors disabled:opacity-50"
                    >
                        {action.label}
                    </button>
                ))}
            </div>
        </div>
    );
}
