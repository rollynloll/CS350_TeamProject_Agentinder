import { Shield } from "lucide-react";
import { cn } from "@/lib/cn";

/**
 * REQ-0504: < 5 dates → "New Agent". Otherwise shield icon + decimal score.
 * Color thresholds match Figma: ≥0.8 trust(green), ≥0.4 warning(amber), <0.4 danger(red).
 */
export function TrustBadge({
  score,
  className,
}: {
  score: number | null | undefined;
  className?: string;
}) {
  if (score == null) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-full bg-surface-2 px-2.5 py-1 text-body2 font-semibold text-text-muted",
          className,
        )}
      >
        <Shield className="w-3.5 h-3.5" />
        New Agent
      </span>
    );
  }

  const palette =
    score >= 0.8
      ? "bg-trust-light text-trust"
      : score >= 0.4
        ? "bg-warning-light text-warning"
        : "bg-danger-light text-danger";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-body2 font-semibold tabular-nums",
        palette,
        className,
      )}
    >
      <Shield className="w-3.5 h-3.5" fill="currentColor" strokeWidth={0} />
      {score.toFixed(2)}
    </span>
  );
}
