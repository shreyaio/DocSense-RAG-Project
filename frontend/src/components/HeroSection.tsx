"use client";

import { motion } from "framer-motion";

interface HeroSectionProps {
    onGetStarted: () => void;
}

export default function HeroSection({ onGetStarted }: HeroSectionProps) {
    return (
        <section className="h-screen w-full flex items-center justify-center px-6 md:px-12 lg:px-20">
            <div className="w-full max-w-[1400px] grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
                {/* LEFT — Editorial Image */}
                <motion.div
                    className="lg:col-span-6 relative"
                    initial={{ opacity: 0, x: -40 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.8, ease: [0.4, 0, 0.2, 1] }}
                >
                    <div className="relative rounded-[24px] overflow-hidden aspect-[4/3] bg-bg-secondary shadow-elevated">
                        {/* PLACEHOLDER — Replace /hero.png with your editorial image */}
                        <img
                            src="hero.jpeg"
                            alt="DocSense AI Document Intelligence"
                            className="w-full h-full object-cover"
                        />
                        {/* Dark gradient overlay */}
                        <div className="absolute inset-0 bg-gradient-to-t from-bg-primary/60 via-transparent to-transparent" />
                        <div className="absolute inset-0 bg-gradient-to-r from-bg-primary/30 to-transparent" />

                        {/* Subtle glow accent */}
                        <div className="absolute -bottom-20 -right-20 w-[300px] h-[300px] rounded-full bg-accent/5 blur-[80px]" />
                    </div>
                </motion.div>

                {/* RIGHT — Content */}
                <motion.div
                    className="lg:col-span-6 flex flex-col gap-8"
                    initial={{ opacity: 0, x: 40 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.8, delay: 0.15, ease: [0.4, 0, 0.2, 1] }}
                >
                    {/* Pill badge */}
                    <motion.div
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4, duration: 0.5 }}
                    >
                        <span className="pill-badge">
                            <svg
                                width="14"
                                height="14"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                            >
                                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                                <path d="M2 17l10 5 10-5" />
                                <path d="M2 12l10 5 10-5" />
                            </svg>
                            AI-Powered RAG
                        </span>
                    </motion.div>

                    {/* Headline */}
                    <motion.h1
                        className="font-serif text-[clamp(36px,5vw,68px)] leading-[1.08] tracking-[-0.02em] text-text-primary"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5, duration: 0.6 }}
                    >
                        Build Beyond{" "}
                        <span className="text-accent italic">Documents</span>
                        <br />
                        Understand Beyond{" "}
                        <span className="text-text-secondary">Keywords</span>
                    </motion.h1>

                    {/* Subtext */}
                    <motion.p
                        className="text-text-secondary text-[16px] leading-relaxed max-w-[440px]"
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.65, duration: 0.5 }}
                    >
                        Upload your documents and ask questions in natural language.
                        DocSense retrieves precise, cited answers grounded in your content —
                        not hallucinations.
                    </motion.p>

                    {/* CTA */}
                    <motion.div
                        initial={{ opacity: 0, y: 16 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.8, duration: 0.5 }}
                    >
                        <button
                            id="hero-cta"
                            onClick={onGetStarted}
                            className="btn-primary text-[15px]"
                        >
                            Get Started
                        </button>
                    </motion.div>
                </motion.div>
            </div>

            {/* Background radial glow */}
            <div className="fixed inset-0 pointer-events-none -z-10">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full bg-accent/[0.02] blur-[120px]" />
            </div>
        </section>
    );
}
