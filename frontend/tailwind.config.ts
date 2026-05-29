import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17201b",
        line: "#d9ded8",
        field: "#f7f8f5",
        action: "#0f6b4f",
        warning: "#9a4f18",
      },
    },
  },
  plugins: [],
};

export default config;
