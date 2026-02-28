"use client";

import { useState, useRef, useCallback } from "react";
import { motion } from "framer-motion";

interface UploadPanelProps {
    onFileSelected: (file: File) => void;
}

export default function UploadPanel({ onFileSelected }: UploadPanelProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            e.stopPropagation();
            setIsDragging(false);

            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type === "application/pdf") {
                setSelectedFile(files[0]);
                onFileSelected(files[0]);
            }
        },
        [onFileSelected]
    );

    const handleFileChange = useCallback(
        (e: React.ChangeEvent<HTMLInputElement>) => {
            const files = e.target.files;
            if (files && files.length > 0) {
                setSelectedFile(files[0]);
                onFileSelected(files[0]);
            }
        },
        [onFileSelected]
    );

    const formatSize = (bytes: number) => {
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    return (
        <motion.div
            className="h-screen w-full flex items-center justify-center px-6"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
        >
            <div className="w-full max-w-[560px]">
                {/* Dropzone */}
                <motion.div
                    className={`dropzone rounded-panel p-12 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-300 ${isDragging ? "active" : ""
                        }`}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => inputRef.current?.click()}
                    whileHover={{ scale: 1.005 }}
                    whileTap={{ scale: 0.995 }}
                >
                    <input
                        ref={inputRef}
                        type="file"
                        accept=".pdf"
                        onChange={handleFileChange}
                        className="hidden"
                        id="file-upload"
                    />

                    {/* Upload icon */}
                    <motion.div
                        className="mb-6"
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.2, duration: 0.4 }}
                    >
                        <div className="w-16 h-16 rounded-2xl bg-accent/10 flex items-center justify-center">
                            <svg
                                width="28"
                                height="28"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="#F97316"
                                strokeWidth="1.5"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                            >
                                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                                <polyline points="17 8 12 3 7 8" />
                                <line x1="12" y1="3" x2="12" y2="15" />
                            </svg>
                        </div>
                    </motion.div>

                    {/* Text */}
                    <h3 className="text-text-primary text-lg font-medium mb-2">
                        Upload your PDF to begin analysis
                    </h3>
                    <p className="text-text-muted text-sm mb-6">
                        Drag &amp; drop or click to browse
                    </p>

                    {/* File info if selected */}
                    {selectedFile && (
                        <motion.div
                            className="glass-card px-4 py-3 flex items-center gap-3 w-full max-w-[360px]"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                        >
                            <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center flex-shrink-0">
                                <svg
                                    width="16"
                                    height="16"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="#F97316"
                                    strokeWidth="2"
                                >
                                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                                    <polyline points="14 2 14 8 20 8" />
                                </svg>
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-text-primary text-sm truncate">
                                    {selectedFile.name}
                                </p>
                                <p className="text-text-muted text-xs">
                                    {formatSize(selectedFile.size)}
                                </p>
                            </div>
                        </motion.div>
                    )}
                </motion.div>

                {/* Bottom note */}
                <motion.p
                    className="text-text-faint text-xs text-center mt-4"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4 }}
                >
                    Supported format: PDF · Max size: 50 MB
                </motion.p>
            </div>
        </motion.div>
    );
}
