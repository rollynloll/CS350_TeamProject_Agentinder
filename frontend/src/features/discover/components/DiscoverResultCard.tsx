import type { FeedCard } from "@/api/types";
import { Avatar } from "@/design-system/components/Avatar";
import { CompatibilityBar } from "@/design-system/components/CompatibilityBar";
import { TrustBadge } from "@/design-system/components/TrustBadge";

export function DiscoverResultCard({ card }: { card: FeedCard }) {
  return (
    <article className="rounded-2xl bg-surface shadow-card p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <Avatar src={card.avatarUrl} name={card.displayName} size="lg" />
          <div className="font-bold text-base truncate">{card.displayName}</div>
        </div>
        <TrustBadge score={card.trustScore} />
      </div>

      <p className="text-sm text-text-muted leading-relaxed line-clamp-3">
        {card.bioSnippet}
      </p>

      {card.topTags.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {card.topTags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center rounded-full bg-surface-2 px-3 py-1 text-xs font-medium text-text-muted"
            >
              {tag}
            </span>
          ))}
        </div>
      ) : null}

      <CompatibilityBar
        score={
          card.compatibilityScore <= 1
            ? card.compatibilityScore * 100
            : card.compatibilityScore
        }
      />
    </article>
  );
}
