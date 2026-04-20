import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // FPL green palette
        fpl: {
          green: "#00ff87",
          purple: "#37003c",
          "purple-light": "#4a0558",
        },
      },
    },
  },
  plugins: [],
};

export default config;
