import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#2E7D32",
          foreground: "#FFFFFF",
        },
        accent: {
          DEFAULT: "#1565C0",
          foreground: "#FFFFFF",
        },
      },
      borderRadius: {
        lg: "0.75rem",
      },
    },
  },
  plugins: [],
};

export default config;
