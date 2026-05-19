import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--color-bg)",
        surface: "var(--color-surface)",
        "surface-2": "var(--color-surface-2)",
        border: "var(--color-border)",
        text: "var(--color-text)",
        "text-muted": "var(--color-text-muted)",
        primary: {
          DEFAULT: "var(--color-primary)",
          fg: "var(--color-primary-fg)",
        },
        danger: "var(--color-danger)",
        success: "var(--color-success)",
        warning: "var(--color-warning)",
        // Relationship tier colors
        "tier-stranger": "var(--color-tier-stranger)",
        "tier-acquaintance": "var(--color-tier-acquaintance)",
        "tier-colleague": "var(--color-tier-colleague)",
        "tier-trusted": "var(--color-tier-trusted)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        DEFAULT: "var(--radius)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        elevated: "var(--shadow-elevated)",
      },
      fontFamily: {
        sans: ["Inter", "Pretendard", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
