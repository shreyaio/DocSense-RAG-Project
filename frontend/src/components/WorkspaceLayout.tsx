"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import PdfViewer from "./PdfViewer";
import ChatWindow from "./ChatWindow";
import SummaryPanel from "./SummaryPanel";
import type { Citation } from "@/lib/api-client";

interface WorkspaceLayoutProps {
    docId: string;
    pdfUrl: string;
    fileName: string;
}

export default function WorkspaceLayout({
    docId,
    pdfUrl,
    fileName,
}: WorkspaceLayoutProps) {
    // Panel sizes (percentages)
    const [leftWidth, setLeftWidth] = useState(50); // % of total width
    const [topHeight, setTopHeight] = useState(55); // % of right panel height
    const [citations, setCitations] = useState<Citation[]>([]);

    // Resize refs
    const containerRef = useRef<HTMLDivElement>(null);
    const isDraggingV = useRef(false);
    const isDraggingH = useRef(false);

    const handleCitationsUpdate = useCallback((newCitations: Citation[]) => {
        setCitations(newCitations);
    }, []);

    // Vertical resize (left ↔ right)
    const startVerticalResize = useCallback(
        (e: React.MouseEvent) => {
            e.preventDefault();
            isDraggingV.current = true;
            document.body.style.cursor = "col-resize";
            document.body.style.userSelect = "none";

            const handleMove = (moveEvent: MouseEvent) => {
                if (!isDraggingV.current || !containerRef.current) return;
                const rect = containerRef.current.getBoundingClientRect();
                const pct = ((moveEvent.clientX - rect.left) / rect.width) * 100;
                setLeftWidth(Math.min(Math.max(pct, 25), 75));
            };

            const handleUp = () => {
                isDraggingV.current = false;
                document.body.style.cursor = "";
                document.body.style.userSelect = "";
                document.removeEventListener("mousemove", handleMove);
                document.removeEventListener("mouseup", handleUp);
            };

            document.addEventListener("mousemove", handleMove);
            document.addEventListener("mouseup", handleUp);
        },
        []
    );

    // Horizontal resize (chat ↔ summary on right)
    const startHorizontalResize = useCallback(
        (e: React.MouseEvent) => {
            e.preventDefault();
            isDraggingH.current = true;
            document.body.style.cursor = "row-resize";
            document.body.style.userSelect = "none";

            const rightPanel = (e.target as HTMLElement).parentElement;
            if (!rightPanel) return;

            const handleMove = (moveEvent: MouseEvent) => {
                if (!isDraggingH.current) return;
                const rect = rightPanel.getBoundingClientRect();
                const pct = ((moveEvent.clientY - rect.top) / rect.height) * 100;
                setTopHeight(Math.min(Math.max(pct, 25), 75));
            };

            const handleUp = () => {
                isDraggingH.current = false;
                document.body.style.cursor = "";
                document.body.style.userSelect = "";
                document.removeEventListener("mousemove", handleMove);
                document.removeEventListener("mouseup", handleUp);
            };

            document.addEventListener("mousemove", handleMove);
            document.addEventListener("mouseup", handleUp);
        },
        []
    );

    return (
        <motion.div
            ref={containerRef}
            className="h-screen w-full flex overflow-hidden bg-bg-primary"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
        >
            {/* LEFT — PDF Preview */}
            <div
                className="h-full overflow-hidden bg-bg-secondary border-r border-border-subtle"
                style={{ width: `${leftWidth}%` }}
            >
                <PdfViewer pdfUrl={pdfUrl} fileName={fileName} />
            </div>

            {/* Vertical resize handle */}
            <div
                className="resize-handle-v"
                onMouseDown={startVerticalResize}
            />

            {/* RIGHT — Chat + Summary */}
            <div
                className="h-full flex flex-col overflow-hidden"
                style={{ width: `${100 - leftWidth}%` }}
            >
                {/* Top — Chat */}
                <div
                    className="overflow-hidden bg-bg-secondary"
                    style={{ height: `${topHeight}%` }}
                >
                    <ChatWindow docId={docId} onCitationsUpdate={handleCitationsUpdate} />
                </div>

                {/* Horizontal resize handle */}
                <div
                    className="resize-handle-h"
                    onMouseDown={startHorizontalResize}
                />

                {/* Bottom — Summary */}
                <div
                    className="overflow-hidden bg-bg-secondary border-t border-border-subtle"
                    style={{ height: `${100 - topHeight}%` }}
                >
                    <SummaryPanel docId={docId} />
                </div>
            </div>
        </motion.div>
    );
}
