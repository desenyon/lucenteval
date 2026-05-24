import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Backgrounds
        "oled-base": "#000000",
        "oled-1":    "#050505",
        "oled-2":    "#080808",
        "oled-3":    "#0B0B0B",
        "oled-4":    "#101010",
        // Accents
        "neon-pink":    "#FF006E",
        "neon-pink-2":  "#FF4D9D",
        "electric":     "#7B2EFF",
        "electric-2":   "#B026FF",
        "deep-blue":    "#0066FF",
        "deep-blue-2":  "#00A3FF",
        "lime":         "#D6FF00",
        "cyan":         "#00E5FF",
        "orange":       "#FF9B42",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
      borderRadius: {
        card:   "32px",
        widget: "22px",
        pill:   "999px",
      },
      backdropBlur: {
        card: "40px",
        heavy: "80px",
      },
      boxShadow: {
        glow:   "0 0 60px rgba(255,0,110,0.18), 0 0 120px rgba(0,102,255,0.12)",
        purple: "0 0 40px rgba(123,46,255,0.3)",
        blue:   "0 0 40px rgba(0,102,255,0.25)",
        cyan:   "0 0 40px rgba(0,229,255,0.2)",
      },
      animation: {
        "fade-up":     "fade-up 500ms cubic-bezier(0.22,1,0.36,1) both",
        "pulse-glow":  "pulse-glow 2s ease-in-out infinite",
        "spin-slow":   "spin-slow 8s linear infinite",
      },
    },
  },
  plugins: [],
};
export default config;
