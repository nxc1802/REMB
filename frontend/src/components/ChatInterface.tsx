// ChatInterface Component - AI Chat for layout questions
import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles } from 'lucide-react';
import type { ChatMessage } from '../types';

interface ChatInterfaceProps {
    messages: ChatMessage[];
    onSendMessage: (message: string) => void;
    loading: boolean;
    disabled: boolean;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({
    messages,
    onSendMessage,
    loading,
    disabled,
}) => {
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (input.trim() && !loading && !disabled) {
            onSendMessage(input.trim());
            setInput('');
        }
    };

    const suggestedQuestions = [
        "What's the difference between the options?",
        "Which layout do you recommend?",
        "How does the optimization work?",
        "What are the compliance requirements?",
    ];

    return (
        <div className="chat-interface">
            <div className="chat-header">
                <Bot size={20} />
                <h3>AI Assistant</h3>
                <Sparkles size={16} className="sparkle" />
            </div>

            <div className="chat-messages">
                {messages.length === 0 ? (
                    <div className="chat-welcome">
                        <Bot size={40} className="welcome-icon" />
                        <h4>Ask about your layouts</h4>
                        <p>I can help you understand optimization options, metrics, and compliance.</p>

                        <div className="suggested-questions">
                            {suggestedQuestions.map((q, i) => (
                                <button
                                    key={i}
                                    className="suggested-btn"
                                    onClick={() => onSendMessage(q)}
                                    disabled={disabled || loading}
                                >
                                    {q}
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    messages.map((msg, index) => (
                        <div key={index} className={`message ${msg.role}`}>
                            <div className="message-icon">
                                {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                            </div>
                            <div className="message-content">
                                <div className="message-text">{msg.content}</div>
                                {msg.role === 'assistant' && msg.model && (
                                    <div className={`model-badge ${msg.model === 'gemini-2.0-flash' ? 'gemini' : 'fallback'}`}>
                                        {msg.model === 'gemini-2.0-flash' ? '🤖 Powered by Gemini' : '💬 Fallback Mode'}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))
                )}

                {loading && (
                    <div className="message assistant loading">
                        <div className="message-icon">
                            <Bot size={16} />
                        </div>
                        <div className="message-content">
                            <div className="typing-indicator">
                                <span></span>
                                <span></span>
                                <span></span>
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            <form className="chat-input-form" onSubmit={handleSubmit}>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={disabled ? "Upload a site first..." : "Ask about your layouts..."}
                    disabled={loading || disabled}
                    className="chat-input"
                />
                <button
                    type="submit"
                    disabled={!input.trim() || loading || disabled}
                    className="btn btn-send"
                >
                    <Send size={18} />
                </button>
            </form>
        </div>
    );
};

export default ChatInterface;
