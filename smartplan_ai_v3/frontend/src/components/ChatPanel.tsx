'use client';

import React, { useState, useRef, useEffect } from 'react';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
}

interface ChatPanelProps {
    onSend: (message: string) => Promise<string>;
    isLoading?: boolean;
    placeholder?: string;
}

export default function ChatPanel({
    onSend,
    isLoading = false,
    placeholder = "Nhập yêu cầu của bạn...",
}: ChatPanelProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMessage = input.trim();
        setInput('');
        setLoading(true);

        // Add user message
        setMessages(prev => [...prev, {
            role: 'user',
            content: userMessage,
            timestamp: new Date(),
        }]);

        try {
            const response = await onSend(userMessage);

            // Add assistant message
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: response,
                timestamp: new Date(),
            }]);
        } catch (error) {
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: `Lỗi: ${error instanceof Error ? error.message : 'Unknown error'}`,
                timestamp: new Date(),
            }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full bg-gray-900 rounded-lg border border-gray-700">
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-700">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    <span className="text-2xl">🤖</span>
                    AI Spatial Planner
                </h3>
                <p className="text-xs text-gray-400">Powered by MegaLLM</p>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[300px]">
                {messages.length === 0 && (
                    <div className="text-center text-gray-500 py-8">
                        <p className="text-4xl mb-2">💬</p>
                        <p>Hãy chọn một Block và nhập yêu cầu</p>
                        <p className="text-sm mt-2">Ví dụ: "Thêm 2 nhà kho lạnh"</p>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`max-w-[80%] rounded-lg px-4 py-2 ${msg.role === 'user'
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-gray-700 text-gray-100'
                                }`}
                        >
                            <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                            <p className="text-xs opacity-50 mt-1">
                                {msg.timestamp.toLocaleTimeString()}
                            </p>
                        </div>
                    </div>
                ))}

                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-gray-700 rounded-lg px-4 py-2">
                            <div className="flex items-center gap-2">
                                <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
                                <span className="text-gray-300 text-sm">Đang xử lý...</span>
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="p-4 border-t border-gray-700">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={placeholder}
                        disabled={loading || isLoading}
                        className="flex-1 bg-gray-800 text-white px-4 py-2 rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none disabled:opacity-50"
                    />
                    <button
                        type="submit"
                        disabled={loading || isLoading || !input.trim()}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        Gửi
                    </button>
                </div>
            </form>
        </div>
    );
}
