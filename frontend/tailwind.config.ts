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
        text: {
          DEFAULT: "var(--color-text)",
          muted: "var(--color-text-muted)",
          subtle: "var(--color-text-subtle)",
        },
        "text-muted": "var(--color-text-muted)",
        "text-subtle": "var(--color-text-subtle)",
        primary: {
          DEFAULT: "var(--color-primary)",
          fg: "var(--color-primary-fg)",
        },
        trust: {
          DEFAULT: "var(--color-trust)",
          light: "var(--color-trust-light)",
        },
        warning: {
          DEFAULT: "var(--color-warning)",
          light: "var(--color-warning-light)",
        },
        danger: {
          DEFAULT: "var(--color-danger)",
          light: "var(--color-danger-light)",
        },
        success: "var(--color-success)",
        // Relationship tier colors (fg + bg pairs)
        "tier-stranger": "var(--color-tier-stranger)",
        "tier-stranger-bg": "var(--color-tier-stranger-bg)",
        "tier-acquaintance": "var(--color-tier-acquaintance)",
        "tier-acquaintance-bg": "var(--color-tier-acquaintance-bg)",
        "tier-colleague": "var(--color-tier-colleague)",
        "tier-colleague-bg": "var(--color-tier-colleague-bg)",
        "tier-trusted": "var(--color-tier-trusted)",
        "tier-trusted-bg": "var(--color-tier-trusted-bg)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        DEFAULT: "var(--radius)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
        full: "var(--radius-full)",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        elevated: "var(--shadow-elevated)",
      },
      fontFamily: {
        sans: ["Inter", "Pretendard", "system-ui", "sans-serif"],
      },
      maxWidth: {
        mobile: "393px",
      },
    },
  },
  plugins: [],
};

export default config;
