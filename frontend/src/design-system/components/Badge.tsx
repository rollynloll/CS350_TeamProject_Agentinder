import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Tone = "neutral" | "primary" | "success" | "danger" | "warning" | "info";

const toneClass: Record<Tone, string> = {
  neutral: "bg-surface-2 text-text",
  primary: "bg-primary/10 text-primary",
  success: "bg-success/10 text-success",
  danger: "bg-danger/10 text-danger",
  warning: "bg-warning/10 text-warning",
  info: "bg-tier-acquaintance/15 text-tier-acquaintance",
};

export function Badge({
  className,
  tone = "neutral",
  ...rest
}: HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
        toneClass[tone],
        className,
      )}
      {...rest}
    />
  );
}
