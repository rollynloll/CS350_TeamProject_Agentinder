import type { Tier } from "@/api/types";
import { cn } from "@/lib/cn";

const map: Record<Tier, { label: string; color: string }> = {
  stranger: {
    label: "Stranger",
    color: "bg-tier-stranger-bg text-tier-stranger-text",
  },
  acquaintance: {
    label: "Acquaintance",
    color: "bg-tier-acquaintance-bg text-tier-acquaintance-text",
  },
  colleague: {
    label: "Colleague",
    color: "bg-tier-colleague-bg text-tier-colleague-text",
  },
  trusted_partner: {
    label: "Trusted Partner",
    color: "bg-tier-trusted-bg text-tier-trusted-text",
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
        "inline-flex items-center justify-center rounded-[8px] px-2 py-1 text-[10px] leading-[1.4] font-semibold",
        item.color,
        className,
      )}
    >
      {item.label}
    </span>
  );
}
