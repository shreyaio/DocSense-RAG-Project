"use client";

interface PdfViewerProps {
    pdfUrl: string;
    fileName: string;
}

export default function PdfViewer({ pdfUrl, fileName }: PdfViewerProps) {
    return (
        <div className="flex flex-col h-full">
            {/* Title bar */}
            <div className="flex-shrink-0 px-5 py-3.5 border-b border-border-subtle flex items-center gap-3">
                <div className="w-7 h-7 rounded-lg bg-accent/10 flex items-center justify-center flex-shrink-0">
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
                </div>
                <span className="text-text-primary text-sm font-medium truncate">
                    {fileName}
                </span>
            </div>

            {/* PDF iframe */}
            <div className="flex-1 p-3">
                <iframe
                    src={pdfUrl}
                    title="PDF Preview"
                    className="w-full h-full pdf-frame rounded-xl"
                />
            </div>
        </div>
    );
}
