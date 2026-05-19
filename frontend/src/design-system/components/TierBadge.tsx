import type { Tier } from "@/api/types";
import { cn } from "@/lib/cn";

const map: Record<Tier, { label: string; color: string }> = {
  stranger: {
    label: "Stranger",
    color: "bg-tier-stranger-bg text-tier-stranger",
  },
  acquaintance: {
    label: "Acquaintance",
    color: "bg-tier-acquaintance-bg text-tier-acquaintance",
  },
  colleague: {
    label: "Colleague",
    color: "bg-tier-colleague-bg text-tier-colleague",
  },
  trusted_partner: {
    label: "Trusted Partner",
    color: "bg-tier-trusted-bg text-tier-trusted",
  },
};

export function TierBadge({
  tier,
  className,
}: {
  tier: Tier;
  className?: string;
}) {
  const item = map[tier];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
        item.color,
        className,
      )}
    >
      {item.label}
    </span>
  );
}
