/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        cyan: {
          DEFAULT: "#00B4D8",
          50: "#E0F7FC",
          100: "#B3EDF7",
          200: "#80E2F2",
          300: "#4DD6EC",
          400: "#26CCE8",
          500: "#00B4D8",
          600: "#009FBF",
          700: "#0087A3",
          800: "#006F87",
          900: "#00576B",
        },
        slate: {
          850: "#172033",
          950: "#0B1120",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      animation: {
        "count-up": "countUp 1s ease-out forwards",
        shimmer: "shimmer 1.5s infinite",
        "fade-in": "fadeIn 0.4s ease-out",
        "slide-in": "slideIn 0.35s cubic-bezier(0.16, 1, 0.3, 1)",
      },
      keyframes: {
        countUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideIn: {
          "0%": { transform: "translateX(100%)", opacity: "0" },
          "100%": { transform: "translateX(0)", opacity: "1" },
        },
      },
      boxShadow: {
        card: "0 4px 24px -4px rgba(0, 180, 216, 0.08)",
        glow: "0 0 20px rgba(0, 180, 216, 0.3)",
      },
    },
  },
  plugins: [],
};
