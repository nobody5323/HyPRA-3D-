import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 情绪主题色（MoodIndicator / 背景光效使用）
        mood: {
          happy: "#f6c177",
          calm: "#8fb8c9",
          sad: "#7c8ba1",
          anxious: "#e0a075",
          tired: "#6b7a99",
          angry: "#c97676",
          surprised: "#d8b46a",
          neutral: "#9aa5b1",
        },
      },
      animation: {
        "breathe-in": "breathe 4s ease-in-out infinite",
        "sound-wave": "wave 1.2s ease-in-out infinite",
      },
      keyframes: {
        breathe: {
          "0%, 100%": { opacity: "0.55", transform: "scale(1)" },
          "50%": { opacity: "0.9", transform: "scale(1.03)" },
        },
        wave: {
          "0%, 100%": { transform: "scaleY(0.4)" },
          "50%": { transform: "scaleY(1)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
