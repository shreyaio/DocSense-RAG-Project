"use client";

import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { getIngestionStatus } from "@/lib/api-client";

interface ProcessingViewProps {
    fileName: string;
    jobId: string;
    onComplete: (docId: string) => void;
    onError: (message: string) => void;
}

const STAGE_MESSAGES: Record<number, string> = {
    0: "Initializing pipeline…",
    5: "Starting document processing…",
    25: "Parsing document structure…",
    35: "Detecting headings & sections…",
    50: "Chunking content into segments…",
    55: "Building chunk metadata…",
    80: "Generating embeddings…",
    90: "Indexing vectors & building search index…",
    100: "Complete!",
};

function getStageMessage(progress: number): string {
    const stages = Object.keys(STAGE_MESSAGES)
        .map(Number)
        .sort((a, b) => a - b);
    let msg = STAGE_MESSAGES[0];
    for (const s of stages) {
        if (progress >= s) msg = STAGE_MESSAGES[s];
    }
    return msg;
}

export default function ProcessingView({
    fileName,
    jobId,
    onComplete,
    onError,
}: ProcessingViewProps) {
    const [progress, setProgress] = useState(0);
    const [message, setMessage] = useState("Initializing pipeline…");
    const [status, setStatus] = useState<string>("pending");
    const pollRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        let cancelled = false;

        const poll = async () => {
            try {
                const job = await getIngestionStatus(jobId);
                if (cancelled) return;

                setProgress(job.progress);
                setStatus(job.status);
                setMessage(job.message || getStageMessage(job.progress));

                if (job.status === "completed") {
                    if (pollRef.current) clearInterval(pollRef.current);
                    setTimeout(() => onComplete(job.doc_id), 800);
                    return;
                }

                if (job.status === "failed") {
                    if (pollRef.current) clearInterval(pollRef.current);
                    onError(job.message || "Ingestion failed");
                    return;
                }
            } catch {
                // Backend not available — keep polling
            }
        };

        pollRef.current = setInterval(poll, 1500);
        poll(); // immediate first call

        return () => {
            cancelled = true;
            if (pollRef.current) clearInterval(pollRef.current);
        };
    }, [jobId, onComplete, onError]);

    return (
        <motion.div
            className="h-screen w-full flex items-center justify-center px-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
        >
            <div className="w-full max-w-[480px]">
                {/* Card */}
                <div className="glass-panel p-10 flex flex-col items-center text-center">
                    {/* Pulsing icon */}
                    <motion.div
                        className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center mb-8"
                        animate={{
                            boxShadow: [
                                "0 0 20px rgba(249, 115, 22, 0.1)",
                                "0 0 40px rgba(249, 115, 22, 0.25)",
                                "0 0 20px rgba(249, 115, 22, 0.1)",
                            ],
                        }}
                        transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                    >
                        <svg
                            width="28"
                            height="28"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="#F97316"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            className={status === "processing" ? "animate-spin" : ""}
                            style={{ animationDuration: "3s" }}
                        >
                            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                        </svg>
                    </motion.div>

                    {/* File name */}
                    <div className="glass-card px-4 py-2.5 mb-8 inline-flex items-center gap-2.5">
                        <svg
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="#F97316"
                            strokeWidth="2"
                        >
                            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                        </svg>
                        <span className="text-text-primary text-sm truncate max-w-[280px]">
                            {fileName}
                        </span>
                    </div>

                    {/* Progress bar */}
                    <div className="w-full mb-4">
                        <div className="progress-track">
                            <motion.div
                                className="progress-fill"
                                initial={{ width: 0 }}
                                animate={{ width: `${progress}%` }}
                                transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
                            />
                        </div>
                    </div>

                    {/* Progress text */}
                    <div className="flex items-center justify-between w-full mb-2">
                        <AnimatePresence mode="wait">
                            <motion.p
                                key={message}
                                className="text-text-secondary text-sm"
                                initial={{ opacity: 0, y: 6 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -6 }}
                                transition={{ duration: 0.25 }}
                            >
                                {message}
                            </motion.p>
                        </AnimatePresence>
                        <span className="text-text-muted text-xs font-mono">
                            {progress}%
                        </span>
                    </div>
                </div>
            </div>
        </motion.div>
    );
}
