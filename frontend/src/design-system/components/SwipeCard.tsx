import type { FeedCard } from "@/api/types";
import { Avatar } from "./Avatar";
import { Badge } from "./Badge";
import { CompatibilityRing } from "./CompatibilityRing";
import { TrustBadge } from "./TrustBadge";

/**
 * SRS §3.1.1 Home/Feed card. Visual only — interaction wiring (swipe gestures,
 * keyboard, etc.) is deferred to the V1 feature implementation.
 */
export function SwipeCard({ card }: { card: FeedCard }) {
  return (
    <div className="rounded-xl border border-border bg-surface shadow-elevated overflow-hidden">
      <div className="p-6 flex flex-col items-center gap-4">
        <Avatar src={card.avatarUrl} name={card.displayName} size="xl" />
        <div className="text-center">
          <h3 className="text-xl font-semibold">{card.displayName}</h3>
          <p className="text-sm text-text-muted mt-1 line-clamp-3">{card.bioSnippet}</p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-1.5">
          {card.topTags.slice(0, 3).map((tag) => (
            <Badge key={tag}>{tag}</Badge>
          ))}
        </div>
        <div className="flex items-center justify-between w-full pt-2 border-t border-border">
          <div className="flex items-center gap-3">
            <CompatibilityRing score={card.compatibilityScore} />
            <span className="text-xs text-text-muted">Compatibility</span>
          </div>
          <TrustBadge score={card.trustScore} />
        </div>
      </div>
    </div>
  );
}
