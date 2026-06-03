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
        tag: "var(--color-tag)",
        primary: {
          DEFAULT: "var(--color-primary)",
          fg: "var(--color-primary-fg)",
          light: "var(--color-primary-light)",
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
        "trust-fg": "var(--color-trust-fg)",
        // Relationship tier colors (solid bg + text pairs)
        "tier-stranger": "var(--color-tier-stranger)",
        "tier-stranger-bg": "var(--color-tier-stranger-bg)",
        "tier-stranger-text": "var(--color-tier-stranger-text)",
        "tier-acquaintance": "var(--color-tier-acquaintance)",
        "tier-acquaintance-bg": "var(--color-tier-acquaintance-bg)",
        "tier-acquaintance-text": "var(--color-tier-acquaintance-text)",
        "tier-colleague": "var(--color-tier-colleague)",
        "tier-colleague-bg": "var(--color-tier-colleague-bg)",
        "tier-colleague-text": "var(--color-tier-colleague-text)",
        "tier-trusted": "var(--color-tier-trusted)",
        "tier-trusted-bg": "var(--color-tier-trusted-bg)",
        "tier-trusted-text": "var(--color-tier-trusted-text)",
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
        float: "var(--shadow-float)",
        inset: "var(--shadow-inset)",
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "Inter", "Pretendard", "system-ui", "sans-serif"],
      },
      fontSize: {
        // Figma type scale
        caption: ["10px", { lineHeight: "1.4" }],
        body2: ["12px", { lineHeight: "1.4" }],
        body1: ["14px", { lineHeight: "1.4" }],
        h3: ["16px", { lineHeight: "1.4" }],
        h2: ["20px", { lineHeight: "1.3" }],
        display: ["32px", { lineHeight: "1.2" }],
      },
      maxWidth: {
        mobile: "393px",
      },
    },
  },
  plugins: [],
};

export default config;
