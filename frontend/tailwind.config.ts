import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-manrope)", "sans-serif"],
        display: ["var(--font-sora)", "sans-serif"]
      },
      colors: {
        surface: "rgb(var(--surface) / <alpha-value>)",
        primary: "rgb(var(--primary) / <alpha-value>)",
        onprimary: "rgb(var(--on-primary) / <alpha-value>)",
        borderline: "rgb(var(--borderline) / <alpha-value>)"
      },
      boxShadow: {
        pill: "0 20px 60px -24px rgba(7, 13, 20, 0.45)",
        glass: "0 16px 40px -20px rgba(16, 24, 40, 0.5)"
      }
    }
  },
  plugins: []
};

export default config;
