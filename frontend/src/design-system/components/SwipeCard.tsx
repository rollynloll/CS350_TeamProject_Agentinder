import { useState } from "react";
import { Heart } from "lucide-react";
import type { FeedCard } from "@/api/types";
import { Avatar } from "./Avatar";
import { TrustTag } from "./TrustTag";
import { cn } from "@/lib/cn";

/**
 * SRS §3.1.1 Home/Feed card — Figma `card` (node 2025:1042). Presentational:
 * the horizontal filmstrip drag lives in the parent (FeedPage). Heart toggles
 * the like state (Figma `like` variant: outline → filled red).
 */
export function SwipeCard({
  card,
  className,
  onLike,
}: {
  card: FeedCard;
  className?: string;
  onLike?: (liked: boolean) => void;
}) {
  const [liked, setLiked] = useState(false);

  const compat =
    card.compatibilityScore <= 1
      ? Math.round(card.compatibilityScore * 100)
      : Math.round(card.compatibilityScore);

  return (
    <article
      className={cn(
        "rounded-[24px] bg-bg shadow-float p-4 flex flex-col gap-2 select-none",
        className,
      )}
    >
      {/* Avatar with like toggle (Figma like variant: outline → filled red) */}
      <div className="relative h-[326px] w-full overflow-hidden rounded-t-[24px] bg-surface-2">
        <Avatar
          src={card.avatarUrl}
          name={card.displayName}
          size="xl"
          className="!w-full !h-full !rounded-t-[24px] !rounded-b-none !text-4xl"
        />
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            const next = !liked;
            setLiked(next);
            onLike?.(next);
          }}
          onPointerDown={(e) => e.stopPropagation()}
          aria-label={liked ? `Unlike ${card.displayName}` : `Like ${card.displayName}`}
          aria-pressed={liked}
          className={cn(
            "absolute bottom-2.5 right-2.5 grid place-items-center w-14 h-14 drop-shadow-[0_2px_4px_rgba(0,0,0,0.4)] active:scale-95 transition-transform",
            liked ? "text-danger" : "text-white",
          )}
        >
          <Heart className="w-8 h-8" fill={liked ? "currentColor" : "none"} strokeWidth={2} />
        </button>
      </div>

      {/* Name + TrustTag (no chevron on the card) */}
      <div className="flex flex-col">
        {card.superLikedYou ? (
          <p className="text-caption font-bold leading-[1.6] text-danger">Liked You</p>
        ) : null}
        <div className="flex items-center gap-2">
          <h3 className="flex-1 min-w-0 truncate text-h3 font-semibold text-text">
            {card.displayName}
          </h3>
          <TrustTag score={card.trustScore} showChevron={false} />
        </div>
      </div>

      {/* Bio */}
      <p className="text-body2 leading-[1.4] text-text-muted line-clamp-2">
        {card.bioSnippet}
      </p>

      {/* Capability tags — Figma tag: bg text-sub/10, px8 py4, radius8, caption */}
      <div className="flex flex-wrap items-center gap-1 min-w-0">
        {card.topTags.slice(0, 4).map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center rounded-[8px] bg-tag px-2 py-1 text-caption font-semibold text-text-muted"
          >
            {tag}
          </span>
        ))}
      </div>

      {/* Compatibility */}
      <div className="flex flex-col">
        <p className="text-caption leading-[1.4] text-text-muted">Compatibility</p>
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
    </article>
  );
}
