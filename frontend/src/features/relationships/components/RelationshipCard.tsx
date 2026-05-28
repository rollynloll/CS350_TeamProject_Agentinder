import type { RelationshipItem } from "@/api/types";
import { Avatar } from "@/design-system/components/Avatar";
import { CompatibilityBar } from "@/design-system/components/CompatibilityBar";
import { TierBadge } from "@/design-system/components/TierBadge";
import { TrustBadge } from "@/design-system/components/TrustBadge";

export function RelationshipCard({
  item,
  compatibilityScore,
}: {
  item: RelationshipItem;
  compatibilityScore?: number;
}) {
  return (
    <article className="rounded-2xl bg-surface shadow-card p-4 flex flex-col gap-3">
      <div>
        <TierBadge tier={item.tier} />
      </div>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <Avatar
            src={item.partnerAgent.avatarUrl}
            name={item.partnerAgent.displayName}
            size="lg"
          />
          <div className="font-bold text-base truncate">
            {item.partnerAgent.displayName}
          </div>
        </div>
        <TrustBadge score={item.partnerAgent.trustScore ?? null} />
      </div>
      {compatibilityScore != null ? (
        <CompatibilityBar score={compatibilityScore} />
      ) : null}
    </article>
  );
}
