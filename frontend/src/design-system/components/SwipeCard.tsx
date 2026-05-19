import { Heart } from "lucide-react";
import type { FeedCard } from "@/api/types";
import { Avatar } from "./Avatar";
import { CompatibilityBar } from "./CompatibilityBar";
import { TrustBadge } from "./TrustBadge";
import { cn } from "@/lib/cn";

/**
 * SRS §3.1.1 Home/Feed card — single-card stack layout matching Figma Main00.
 * Drag/swipe gestures are wired in a follow-up V1 ticket.
 */
export function SwipeCard({
  card,
  className,
  onLike,
}: {
  card: FeedCard;
  className?: string;
  onLike?: () => void;
}) {
  return (
    <article
      className={cn(
        "rounded-2xl bg-surface shadow-card p-5 flex flex-col gap-4",
        className,
      )}
    >
      {card.superLikedYou ? (
        <div className="text-[11px] font-bold tracking-wider text-primary -mb-1">
          SUPER LIKED YOU
        </div>
      ) : null}

      <div className="flex items-start justify-between gap-3">
        <h3 className="text-xl font-bold tracking-tight">{card.displayName}</h3>
        <TrustBadge score={card.trustScore} />
      </div>

      <div className="aspect-square w-full overflow-hidden rounded-xl bg-surface-2">
        <Avatar
          src={card.avatarUrl}
          name={card.displayName}
          size="xl"
          className="!w-full !h-full !rounded-xl !text-4xl"
        />
      </div>

      <p className="text-sm text-text-muted leading-relaxed line-clamp-3">
        {card.bioSnippet}
      </p>

      <div className="flex items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5 min-w-0">
          {card.topTags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center rounded-full bg-surface-2 px-3 py-1 text-xs font-medium text-text-muted"
            >
              {tag}
            </span>
          ))}
        </div>
        <button
          type="button"
          onClick={onLike}
          aria-label={`Like ${card.displayName}`}
          className="shrink-0 p-1.5 rounded-full text-text-subtle hover:text-primary hover:bg-danger-light transition-colors"
        >
          <Heart className="w-6 h-6" strokeWidth={1.75} />
        </button>
      </div>

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
