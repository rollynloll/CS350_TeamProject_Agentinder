import { ChevronDown, Shield } from "lucide-react";
import { cn } from "@/lib/cn";

/**
 * Figma `TrustTag` — solid tier-colored pill with dark text: shield + score
 * + optional chevron (expands to the trust-score detail). Distinct from the
 * tinted `TrustBadge`. REQ-0504: < 5 dates renders a neutral "NEW" tag.
 *
 * Tier by score (Figma trust low/mid/high): ≥0.8 green, ≥0.4 amber, else red.
 */
export function TrustTag({
  score,
  isNew = false,
  showChevron = true,
  className,
}: {
  score: number | null | undefined;
  isNew?: boolean;
  showChevron?: boolean;
  className?: string;
}) {
  if (isNew || score == null) {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1 rounded-[8px] bg-primary px-2 py-1 text-trust-fg",
          className,
        )}
      >
        <Shield className="w-4 h-4" fill="currentColor" strokeWidth={0} />
        <span className="text-body2 font-semibold leading-none">NEW</span>
      </span>
    );
  }

  const bg = score >= 0.8 ? "bg-trust" : score >= 0.4 ? "bg-warning" : "bg-danger";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-[8px] px-2 py-1 text-trust-fg",
        bg,
        className,
      )}
    >
      <Shield className="w-4 h-4" fill="currentColor" strokeWidth={0} />
      <span className="text-body2 font-semibold leading-none tabular-nums">
        {score.toFixed(2)}
      </span>
      {showChevron ? <ChevronDown className="w-3 h-3" strokeWidth={2.5} /> : null}
    </span>
  );
}
