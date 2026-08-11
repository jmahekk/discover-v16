/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bond: "var(--bond)",
        surface: "var(--surface)",
        ink: "var(--ink)",
        graphite: "var(--graphite)",
        rule: "var(--rule)",
        ultra: "var(--ultra)",
        marker: "var(--marker)",
        "marker-soft": "var(--marker-soft)",
      },
      fontFamily: {
        ui: ['"Archivo"', '"Segoe UI"', "system-ui", "sans-serif"],
        reading: ['"STIX Two Text"', "Georgia", "serif"],
        data: ['"IBM Plex Mono"', "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
