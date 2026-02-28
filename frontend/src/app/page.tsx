"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

import HeroSection from "@/components/HeroSection";
import UploadPanel from "@/components/UploadPanel";
import ProcessingView from "@/components/ProcessingView";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import { uploadDocument } from "@/lib/api-client";

type AppState = "hero" | "upload" | "processing" | "workspace";

// Shared transition config
const pageVariants = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -20, filter: "blur(4px)" },
};

const pageTransition = {
    duration: 0.5,
    ease: [0.4, 0, 0.2, 1] as const,
};

export default function Home() {
    const [appState, setAppState] = useState<AppState>("hero");

    // Shared state across views
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [jobId, setJobId] = useState<string>("");
    const [docId, setDocId] = useState<string>("");
    const [pdfUrl, setPdfUrl] = useState<string>("");
    const [fileName, setFileName] = useState<string>("");
    const [error, setError] = useState<string | null>(null);

    /* ============================================
       STATE TRANSITIONS
       ============================================ */

    const handleGetStarted = useCallback(() => {
        setAppState("upload");
    }, []);

    const handleFileSelected = useCallback(async (file: File) => {
        setSelectedFile(file);
        setFileName(file.name);
        setError(null);

        // Create blob URL for PDF preview later
        const blobUrl = URL.createObjectURL(file);
        setPdfUrl(blobUrl);

        // Upload to backend
        try {
            const result = await uploadDocument(file);
            setJobId(result.job_id);
            setDocId(result.doc_id);
            setAppState("processing");
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Upload failed";
            setError(msg);
        }
    }, []);

    const handleProcessingComplete = useCallback((completedDocId: string) => {
        setDocId(completedDocId);
        setAppState("workspace");
    }, []);

    const handleProcessingError = useCallback((message: string) => {
        setError(message);
        setAppState("upload");
    }, []);

    return (
        <main className="relative min-h-screen bg-bg-primary overflow-hidden">
            {/* Ambient background glow */}
            <div className="fixed inset-0 pointer-events-none -z-10">
                <div className="absolute top-[20%] left-[30%] w-[600px] h-[600px] rounded-full bg-accent/[0.015] blur-[150px]" />
                <div className="absolute bottom-[10%] right-[20%] w-[400px] h-[400px] rounded-full bg-accent/[0.01] blur-[120px]" />
            </div>

            {/* Error toast */}
            <AnimatePresence>
                {error && (
                    <motion.div
                        className="fixed top-6 left-1/2 -translate-x-1/2 z-50 glass-card px-5 py-3 flex items-center gap-3 shadow-elevated"
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        transition={{ duration: 0.3 }}
                    >
                        <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="#EF4444"
                            strokeWidth="2"
                        >
                            <circle cx="12" cy="12" r="10" />
                            <line x1="15" y1="9" x2="9" y2="15" />
                            <line x1="9" y1="9" x2="15" y2="15" />
                        </svg>
                        <span className="text-red-400 text-sm">{error}</span>
                        <button
                            onClick={() => setError(null)}
                            className="text-text-muted hover:text-text-primary ml-2 transition-colors"
                        >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <line x1="18" y1="6" x2="6" y2="18" />
                                <line x1="6" y1="6" x2="18" y2="18" />
                            </svg>
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* State-driven views */}
            <AnimatePresence mode="wait">
                {appState === "hero" && (
                    <motion.div
                        key="hero"
                        variants={pageVariants}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                        transition={pageTransition}
                    >
                        <HeroSection onGetStarted={handleGetStarted} />
                    </motion.div>
                )}

                {appState === "upload" && (
                    <motion.div
                        key="upload"
                        variants={pageVariants}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                        transition={pageTransition}
                    >
                        <UploadPanel onFileSelected={handleFileSelected} />
                    </motion.div>
                )}

                {appState === "processing" && (
                    <motion.div
                        key="processing"
                        variants={pageVariants}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                        transition={pageTransition}
                    >
                        <ProcessingView
                            fileName={fileName}
                            jobId={jobId}
                            onComplete={handleProcessingComplete}
                            onError={handleProcessingError}
                        />
                    </motion.div>
                )}

                {appState === "workspace" && (
                    <motion.div
                        key="workspace"
                        variants={pageVariants}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                        transition={pageTransition}
                        className="h-screen"
                    >
                        <WorkspaceLayout
                            docId={docId}
                            pdfUrl={pdfUrl}
                            fileName={fileName}
                        />
                    </motion.div>
                )}
            </AnimatePresence>
        </main>
    );
}
