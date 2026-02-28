import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./src/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                bg: {
                    primary: "#0B0B0D",
                    secondary: "#141417",
                    tertiary: "#1A1A1F",
                    elevated: "#1E1E24",
                },
                accent: {
                    DEFAULT: "#F97316",
                    hover: "#FB923C",
                    muted: "rgba(249, 115, 22, 0.15)",
                    glow: "rgba(249, 115, 22, 0.08)",
                },
                text: {
                    primary: "#F5F5F5",
                    secondary: "#9CA3AF",
                    muted: "#6B7280",
                    faint: "#4B5563",
                },
                border: {
                    subtle: "rgba(255, 255, 255, 0.05)",
                    DEFAULT: "rgba(255, 255, 255, 0.08)",
                    active: "rgba(255, 255, 255, 0.12)",
                },
            },
            fontFamily: {
                serif: ["Playfair Display", "Georgia", "serif"],
                sans: ["Inter", "system-ui", "sans-serif"],
            },
            borderRadius: {
                panel: "20px",
                card: "16px",
                button: "12px",
            },
            boxShadow: {
                glow: "0 0 60px rgba(249, 115, 22, 0.06)",
                "glow-sm": "0 0 30px rgba(249, 115, 22, 0.04)",
                panel: "0 8px 32px rgba(0, 0, 0, 0.4)",
                elevated: "0 16px 64px rgba(0, 0, 0, 0.5)",
            },
            animation: {
                "fade-in": "fadeIn 0.6s cubic-bezier(0.4, 0, 0.2, 1) forwards",
                "slide-up": "slideUp 0.6s cubic-bezier(0.4, 0, 0.2, 1) forwards",
                "slide-down": "slideDown 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards",
                "pulse-glow": "pulseGlow 2s ease-in-out infinite",
                "progress-fill": "progressFill 0.5s ease-in-out forwards",
            },
            keyframes: {
                fadeIn: {
                    "0%": { opacity: "0" },
                    "100%": { opacity: "1" },
                },
                slideUp: {
                    "0%": { opacity: "0", transform: "translateY(24px)" },
                    "100%": { opacity: "1", transform: "translateY(0)" },
                },
                slideDown: {
                    "0%": { opacity: "0", transform: "translateY(-16px)" },
                    "100%": { opacity: "1", transform: "translateY(0)" },
                },
                pulseGlow: {
                    "0%, 100%": { boxShadow: "0 0 20px rgba(249, 115, 22, 0.1)" },
                    "50%": { boxShadow: "0 0 40px rgba(249, 115, 22, 0.25)" },
                },
                progressFill: {
                    "0%": { width: "0%" },
                    "100%": { width: "var(--progress-width)" },
                },
            },
        },
    },
    plugins: [],
};

export default config;
