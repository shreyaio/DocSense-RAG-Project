"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { queryDocument, type QueryResponse, type Citation } from "@/lib/api-client";

interface ChatMessage {
    id: string;
    role: "user" | "assistant";
    content: string;
    citations?: Citation[];
    isStreaming?: boolean;
}

interface ChatWindowProps {
    docId: string;
    onCitationsUpdate: (citations: Citation[]) => void;
}

export default function ChatWindow({ docId, onCitationsUpdate }: ChatWindowProps) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [isStreaming, setIsStreaming] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = useCallback(async () => {
        const question = input.trim();
        if (!question || isStreaming) return;

        const userMsg: ChatMessage = {
            id: `user-${Date.now()}`,
            role: "user",
            content: question,
        };

        const assistantMsg: ChatMessage = {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: "",
            isStreaming: true,
        };

        setMessages((prev) => [...prev, userMsg, assistantMsg]);
        setInput("");
        setIsStreaming(true);

        try {
            const response: QueryResponse = await queryDocument(
                {
                    question,
                    doc_ids: [docId],
                    top_k: 5,
                },
                // SSE token callback
                (token: string) => {
                    setMessages((prev) => {
                        const updated = [...prev];
                        const last = updated[updated.length - 1];
                        if (last.role === "assistant") {
                            last.content += token;
                        }
                        return updated;
                    });
                }
            );

            // Finalize message with full response
            setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                    // If non-streaming, set the full answer
                    if (!last.content) last.content = response.answer;
                    last.citations = response.citations;
                    last.isStreaming = false;
                }
                return updated;
            });

            // Push citations to parent
            if (response.citations?.length) {
                onCitationsUpdate(response.citations);
            }
        } catch (err: unknown) {
            const errorMessage = err instanceof Error ? err.message : "An error occurred";
            setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                    last.content = `Sorry, something went wrong: ${errorMessage}`;
                    last.isStreaming = false;
                }
                return updated;
            });
        } finally {
            setIsStreaming(false);
        }
    }, [input, isStreaming, docId, onCitationsUpdate]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex-shrink-0 px-5 py-3.5 border-b border-border-subtle">
                <h3 className="text-text-primary text-sm font-medium tracking-wide flex items-center gap-2">
                    <svg
                        width="15"
                        height="15"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="#F97316"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                    </svg>
                    Document Q&amp;A
                </h3>
            </div>

            {/* Messages */}
            <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto custom-scrollbar px-5 py-4 space-y-4"
            >
                {messages.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center text-center py-12">
                        <div className="w-12 h-12 rounded-xl bg-accent/10 flex items-center justify-center mb-4">
                            <svg
                                width="20"
                                height="20"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="#F97316"
                                strokeWidth="1.5"
                            >
                                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
                            </svg>
                        </div>
                        <p className="text-text-secondary text-sm mb-1">Ask a question about your document</p>
                        <p className="text-text-faint text-xs">
                            Answers are grounded in the uploaded content with citations
                        </p>
                    </div>
                )}

                <AnimatePresence initial={false}>
                    {messages.map((msg) => (
                        <motion.div
                            key={msg.id}
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
                            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                        >
                            <div
                                className={`max-w-[85%] px-4 py-3 text-sm leading-relaxed ${msg.role === "user"
                                        ? "chat-message-user text-text-primary"
                                        : "chat-message-assistant text-text-secondary"
                                    }`}
                            >
                                <p className="whitespace-pre-wrap">{msg.content}</p>

                                {/* Typing indicator */}
                                {msg.isStreaming && !msg.content && (
                                    <div className="flex items-center gap-1.5 py-1">
                                        <div className="typing-dot" />
                                        <div className="typing-dot" />
                                        <div className="typing-dot" />
                                    </div>
                                )}

                                {/* Inline citations */}
                                {msg.citations && msg.citations.length > 0 && (
                                    <div className="mt-3 pt-3 border-t border-border-subtle space-y-1.5">
                                        <p className="text-text-faint text-xs font-medium uppercase tracking-wider mb-1">
                                            Sources
                                        </p>
                                        {msg.citations.map((c, i) => (
                                            <div
                                                key={i}
                                                className="text-xs text-text-muted flex items-center gap-1.5"
                                            >
                                                <span className="text-accent">●</span>
                                                Page {c.page_number}
                                                {c.section_path && (
                                                    <span className="text-text-faint">
                                                        · {c.section_path}
                                                    </span>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>

            {/* Input */}
            <div className="flex-shrink-0 px-4 pb-4 pt-2">
                <div className="flex items-end gap-2 glass-card p-2">
                    <textarea
                        ref={inputRef}
                        id="chat-input"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask about your document…"
                        rows={1}
                        disabled={isStreaming}
                        className="flex-1 bg-transparent text-text-primary text-sm placeholder-text-faint outline-none resize-none py-2 px-3 max-h-[120px]"
                        style={{ minHeight: "36px" }}
                    />
                    <button
                        id="chat-send"
                        onClick={handleSend}
                        disabled={isStreaming || !input.trim()}
                        className="flex-shrink-0 w-9 h-9 rounded-xl bg-accent hover:bg-accent-hover disabled:opacity-30 disabled:hover:bg-accent flex items-center justify-center transition-all duration-200"
                    >
                        <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="white"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        >
                            <line x1="22" y1="2" x2="11" y2="13" />
                            <polygon points="22 2 15 22 11 13 2 9 22 2" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}
