import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Tone = "neutral" | "primary" | "trust" | "warning" | "danger" | "info";

const toneClass: Record<Tone, string> = {
  neutral: "bg-surface-2 text-text-muted",
  primary: "bg-danger-light text-primary",
  trust: "bg-trust-light text-trust",
  warning: "bg-warning-light text-warning",
  danger: "bg-danger-light text-danger",
  info: "bg-tier-acquaintance-bg text-tier-acquaintance",
};

export function Badge({
  className,
  tone = "neutral",
  ...rest
}: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
        toneClass[tone],
        className,
      )}
      {...rest}
    />
  );
}
