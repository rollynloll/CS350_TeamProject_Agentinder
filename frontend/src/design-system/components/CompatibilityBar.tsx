import { cn } from "@/lib/cn";

/**
 * Horizontal compatibility readout: label + bar + big coral number.
 * Accepts either 0–1 or 0–100; values ≤1 are scaled.
 */
export function CompatibilityBar({
  score,
  className,
}: {
  score: number;
  className?: string;
}) {
  const pct = Math.max(0, Math.min(100, score <= 1 ? score * 100 : score));
  const display = Math.round(pct);

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-medium text-text-muted mb-1">
          Compatibility
        </div>
        <div
          className="h-1.5 w-full rounded-full bg-surface-2 overflow-hidden"
          role="progressbar"
          aria-valuenow={display}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="h-full bg-primary transition-[width] duration-300"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
      <span className="text-2xl font-bold text-primary tabular-nums leading-none">
        {display}
      </span>
    </div>
  );
}
