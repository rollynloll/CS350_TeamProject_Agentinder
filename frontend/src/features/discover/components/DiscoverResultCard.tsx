import type { FeedCard } from "@/api/types";
import { Avatar } from "@/design-system/components/Avatar";
import { TrustTag } from "@/design-system/components/TrustTag";

/**
 * Figma `cardsmall` (node 2051:1132) — horizontal search result: square avatar
 * on the left; name + TrustTag, capability tags, and the compatibility bar
 * stacked on the right. Tapping it opens the same detail view as the home card.
 */
export function DiscoverResultCard({
  card,
  onOpen,
}: {
  card: FeedCard;
  onOpen?: () => void;
}) {
  const compat =
    card.compatibilityScore <= 1
      ? Math.round(card.compatibilityScore * 100)
      : Math.round(card.compatibilityScore);

  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex items-stretch w-full text-left overflow-hidden rounded-[16px] bg-bg shadow-float active:scale-[0.99] transition-transform"
    >
      <Avatar
        src={card.avatarUrl}
        name={card.displayName}
        size="xl"
        className="!w-[104px] !h-[104px] !rounded-none shrink-0 !text-h2"
      />
      <div className="flex flex-col gap-2 px-3 py-2 flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="flex-1 min-w-0 truncate text-h3 font-semibold text-text">
            {card.displayName}
          </h3>
          <TrustTag score={card.trustScore} showChevron={false} />
        </div>

        <div className="flex items-center gap-1 min-w-0 overflow-hidden">
          {card.topTags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center rounded-[8px] bg-tag px-2 py-1 text-caption font-semibold text-text-muted whitespace-nowrap"
            >
              {tag}
            </span>
          ))}
        </div>

        <div className="flex items-center gap-4">
          <div className="flex-1 h-1 rounded-full bg-text-muted/20">
            <div
              className="h-1 rounded-full bg-primary"
              style={{ width: `${Math.max(0, Math.min(100, compat))}%` }}
            />
          </div>
          <span className="min-w-[30px] text-right text-h2 font-bold text-primary tabular-nums">
            {compat}
          </span>
        </div>
      </div>
    </button>
  );
}
