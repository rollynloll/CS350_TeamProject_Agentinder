import type { Tier } from "@/api/types";
import { cn } from "@/lib/cn";

const map: Record<Tier, { label: string; color: string }> = {
  stranger: { label: "Stranger", color: "bg-tier-stranger/15 text-tier-stranger" },
  acquaintance: { label: "Acquaintance", color: "bg-tier-acquaintance/15 text-tier-acquaintance" },
  colleague: { label: "Colleague", color: "bg-tier-colleague/15 text-tier-colleague" },
  trusted_partner: { label: "Trusted Partner", color: "bg-tier-trusted/15 text-tier-trusted" },
};

export function TierBadge({ tier }: { tier: Tier }) {
  const item = map[tier];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
        item.color,
      )}
    >
      {item.label}
    </span>
  );
}
