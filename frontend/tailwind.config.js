/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Base surfaces - deep indigo instead of flat gray-black
        ink: "#0A0A16",
        panel: "#161226",
        panel2: "#1D1830",
        rule: "#3C3458",

        // Report "paper" stays warm parchment for contrast against the shell
        paper: "#EDE9DE",
        "paper-dim": "#DFDACB",

        // Text
        ash: "#A79FC4",
        bone: "#F4F0EA",

        // Verdict / semantic accents - punchier, more saturated
        verified: "#2DD4A7",
        plausible: "#F5A93F",
        unverified: "#93A0BD",
        contradicted: "#FB7295",

        // New: pure accent hues used for the aurora backdrop, gradient text,
        // and gradient borders. Named apart from Tailwind's built-in scales
        // so they don't clobber violet-500 etc.
        mystic: "#8C6FF7",
        bloom: "#F45FB0",
        glow: "#5FD1E8",
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        sans: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      boxShadow: {
        paper: "0 1px 0 rgba(0,0,0,0.05), 0 20px 50px -20px rgba(0,0,0,0.6)",
        "glow-amber": "0 0 0 1px rgba(245,169,63,0.45), 0 8px 24px -6px rgba(245,169,63,0.5)",
        "glow-amber-lg": "0 0 0 1px rgba(245,169,63,0.55), 0 14px 44px -8px rgba(245,169,63,0.65)",
        "glow-mystic": "0 0 0 1px rgba(140,111,247,0.4), 0 8px 28px -6px rgba(140,111,247,0.55)",
        "glow-ash": "0 0 0 1px rgba(167,159,196,0.3), 0 6px 18px -6px rgba(0,0,0,0.5)",
        "card": "0 1px 0 rgba(255,255,255,0.05) inset, 0 30px 70px -25px rgba(0,0,0,0.75)",
      },
      keyframes: {
        pulseDot: {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0.35 },
        },
        stampIn: {
          "0%": { opacity: 0, transform: "scale(1.4) rotate(-8deg)" },
          "60%": { opacity: 1, transform: "scale(0.96) rotate(-2deg)" },
          "100%": { opacity: 1, transform: "scale(1) rotate(-2deg)" },
        },
        sealPop: {
          "0%": { opacity: 0, transform: "scale(0.5) rotate(-18deg)" },
          "70%": { opacity: 1, transform: "scale(1.06) rotate(-7deg)" },
          "100%": { opacity: 1, transform: "scale(1) rotate(-8deg)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-150% 0" },
          "100%": { backgroundPosition: "250% 0" },
        },
        glowRing: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(245,169,63,0.35)" },
          "50%": { boxShadow: "0 0 0 6px rgba(245,169,63,0)" },
        },
        auroraDrift1: {
          "0%, 100%": { transform: "translate(0px, 0px) scale(1)" },
          "50%": { transform: "translate(40px, 30px) scale(1.08)" },
        },
        auroraDrift2: {
          "0%, 100%": { transform: "translate(0px, 0px) scale(1)" },
          "50%": { transform: "translate(-35px, -25px) scale(1.05)" },
        },
        gradientPan: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
      },
      animation: {
        pulseDot: "pulseDot 1.4s ease-in-out infinite",
        stampIn: "stampIn 0.35s ease-out",
        sealPop: "sealPop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)",
        shimmer: "shimmer 2.6s ease-in-out infinite",
        glowRing: "glowRing 2.4s ease-in-out infinite",
        auroraDrift1: "auroraDrift1 16s ease-in-out infinite",
        auroraDrift2: "auroraDrift2 19s ease-in-out infinite",
        gradientPan: "gradientPan 6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};