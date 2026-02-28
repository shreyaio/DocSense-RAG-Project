"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { summarizeDocument, type SummarizeResponse } from "@/lib/api-client";

interface SummaryPanelProps {
    docId: string;
}

export default function SummaryPanel({ docId }: SummaryPanelProps) {
    const [mode, setMode] = useState<"summary" | "key_points">("summary");
    const [results, setResults] = useState<Record<string, SummarizeResponse>>({});
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState(false);
    const fetchingRef = useRef(false);

    const fetchSummary = useCallback(
        async (selectedMode: "summary" | "key_points", force: boolean = false) => {
            // If we already have the result OR an error for this mode, do nothing unless forced
            if ((results[selectedMode] || errors[selectedMode]) && !force) return;
            if (fetchingRef.current) return;

            fetchingRef.current = true;
            setLoading(true);

            // Clear current error for this mode if it's a retry
            setErrors(prev => {
                const updated = { ...prev };
                delete updated[selectedMode];
                return updated;
            });

            try {
                const res = await summarizeDocument({
                    doc_id: docId,
                    mode: selectedMode,
                });

                if (res.status === "busy") {
                    setErrors(prev => ({ ...prev, [selectedMode]: res.message || "System is busy." }));
                } else {
                    setResults(prev => ({ ...prev, [selectedMode]: res }));
                }
            } catch (err: unknown) {
                const msg = err instanceof Error ? err.message : "Summarization failed";
                setErrors(prev => ({ ...prev, [selectedMode]: msg }));
            } finally {
                setLoading(false);
                fetchingRef.current = false;
            }
        },
        [docId, results, errors]
    );

    // Initial fetch on mount or doc change
    useEffect(() => {
        // Clear previous doc results when docId changes
        setResults({});
        setErrors({});
    }, [docId]);

    useEffect(() => {
        if (!docId) return;
        fetchSummary(mode);
    }, [docId, mode, fetchSummary]);

    const handleModeSwitch = (newMode: "summary" | "key_points") => {
        setMode(newMode);
        // fetchSummary is already triggered by the useEffect observing 'mode'
    };

    const currentResult = results[mode];
    const currentError = errors[mode];

    return (
        <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex-shrink-0 px-5 py-3.5 border-b border-border-subtle flex items-center justify-between">
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
                        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                        <line x1="16" y1="13" x2="8" y2="13" />
                        <line x1="16" y1="17" x2="8" y2="17" />
                        <polyline points="10 9 9 9 8 9" />
                    </svg>
                    Insights
                </h3>

                {/* Mode toggle */}
                <div className="flex items-center bg-bg-primary/60 rounded-lg p-0.5 gap-0.5">
                    <button
                        id="mode-summary"
                        onClick={() => handleModeSwitch("summary")}
                        className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 ${mode === "summary"
                            ? "bg-accent/15 text-accent"
                            : "text-text-muted hover:text-text-secondary"
                            }`}
                    >
                        Summary
                    </button>
                    <button
                        id="mode-keypoints"
                        onClick={() => handleModeSwitch("key_points")}
                        className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200 ${mode === "key_points"
                            ? "bg-accent/15 text-accent"
                            : "text-text-muted hover:text-text-secondary"
                            }`}
                    >
                        Key Points
                    </button>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto custom-scrollbar px-5 py-5">
                <AnimatePresence mode="wait">
                    {loading && (
                        <motion.div
                            key="loading"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-col items-center justify-center py-16"
                        >
                            <div className="flex items-center gap-2 mb-3">
                                <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
                                <div
                                    className="w-2 h-2 rounded-full bg-accent animate-pulse"
                                    style={{ animationDelay: "0.2s" }}
                                />
                                <div
                                    className="w-2 h-2 rounded-full bg-accent animate-pulse"
                                    style={{ animationDelay: "0.4s" }}
                                />
                            </div>
                            <p className="text-text-muted text-sm">
                                Generating {mode === "summary" ? "summary" : "key points"}…
                            </p>
                        </motion.div>
                    )}

                    {currentError && !loading && (
                        <motion.div
                            key={`error-${mode}`}
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            className={`p-4 ${currentError.includes("busy") ? "alert-warning" : "glass-card border-red-500/20"}`}
                        >
                            <div className="flex items-start gap-3">
                                <svg
                                    width="16"
                                    height="16"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke={currentError.includes("busy") ? "#F97316" : "#F87171"}
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    className="mt-0.5 flex-shrink-0"
                                >
                                    {currentError.includes("busy") ? (
                                        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                                    ) : (
                                        <>
                                            <circle cx="12" cy="12" r="10" />
                                            <line x1="12" y1="8" x2="12" y2="12" />
                                            <line x1="12" y1="16" x2="12.01" y2="16" />
                                        </>
                                    )}
                                </svg>
                                <div className="flex-1">
                                    <p className={`${currentError.includes("busy") ? "text-accent" : "text-red-400"} text-sm leading-relaxed mb-3`}>
                                        {currentError}
                                    </p>
                                    <button
                                        onClick={() => fetchSummary(mode, true)}
                                        className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all ${currentError.includes("busy")
                                            ? "bg-accent/10 hover:bg-accent/20 text-accent border border-accent/20"
                                            : "bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20"
                                            }`}
                                    >
                                        Try Again
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    )}

                    {currentResult && !loading && !currentError && (
                        <motion.div
                            key={`result-${currentResult.mode}`}
                            initial={{ opacity: 0, y: 12 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.35 }}
                        >
                            {currentResult.mode === "summary" ? (
                                /* Executive Summary */
                                <div>
                                    <h4 className="text-text-primary text-base font-medium mb-4 font-serif">
                                        Executive Summary
                                    </h4>
                                    <p className="text-text-secondary text-sm leading-[1.8] whitespace-pre-wrap">
                                        {currentResult.output || ""}
                                    </p>
                                </div>
                            ) : (
                                /* Key Points */
                                <div>
                                    <h4 className="text-text-primary text-base font-medium mb-4 font-serif">
                                        Key Points
                                    </h4>
                                    <ul className="space-y-3">
                                        {(currentResult.output || "")
                                            .split("\n")
                                            .filter((line: string) => line.trim())
                                            .map((point: string, i: number) => (
                                                <motion.li
                                                    key={i}
                                                    initial={{ opacity: 0, x: -8 }}
                                                    animate={{ opacity: 1, x: 0 }}
                                                    transition={{ delay: i * 0.06, duration: 0.3 }}
                                                    className="flex items-start gap-3 text-sm text-text-secondary leading-relaxed"
                                                >
                                                    <span className="w-1.5 h-1.5 rounded-full bg-accent mt-2 flex-shrink-0" />
                                                    <span>{point.replace(/^[-•*]\s*/, "")}</span>
                                                </motion.li>
                                            ))}
                                    </ul>
                                </div>
                            )}

                            {/* Meta info */}
                            <div className="mt-6 pt-4 border-t border-border-subtle flex items-center gap-4">
                                <span className="text-text-faint text-xs">
                                    Model: {currentResult.model_used}
                                </span>
                                <span className="text-text-faint text-xs">
                                    Chunks used: {currentResult.chunk_count_used}
                                </span>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
