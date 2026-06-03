import { useRef, useState, type PointerEvent } from "react";
import { Heart, Star, X } from "lucide-react";
import type { FeedCard, SwipeAction } from "@/api/types";
import { Avatar } from "./Avatar";
import { CompatibilityBar } from "./CompatibilityBar";
import { TrustBadge } from "./TrustBadge";
import { cn } from "@/lib/cn";

/**
 * SRS §3.1.1 Home/Feed card. Swipe right = like, left = pass, up = super-like
 * (drag past the threshold), or use the action buttons.
 */
const THRESHOLD = 96; // px drag distance to commit a swipe

export function SwipeCard({
  card,
  className,
  onSwipe,
}: {
  card: FeedCard;
  className?: string;
  onSwipe?: (action: SwipeAction) => void;
}) {
  const [drag, setDrag] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [exit, setExit] = useState<SwipeAction | null>(null);
  const start = useRef<{ x: number; y: number } | null>(null);

  const commit = (action: SwipeAction) => {
    if (exit) return;
    setExit(action);
    onSwipe?.(action);
  };

  const onPointerDown = (e: PointerEvent<HTMLElement>) => {
    if (exit) return;
    start.current = { x: e.clientX, y: e.clientY };
    setDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const onPointerMove = (e: PointerEvent<HTMLElement>) => {
    if (!start.current) return;
    setDrag({ x: e.clientX - start.current.x, y: e.clientY - start.current.y });
  };

  const onPointerUp = () => {
    if (!start.current) return;
    const { x, y } = drag;
    start.current = null;
    setDragging(false);
    if (-y > THRESHOLD && Math.abs(y) > Math.abs(x)) commit("super_like");
    else if (x > THRESHOLD) commit("like");
    else if (x < -THRESHOLD) commit("pass");
    else setDrag({ x: 0, y: 0 }); // snap back
  };

  const transform = exit
    ? exit === "like"
      ? "translate(140%, -40px) rotate(24deg)"
      : exit === "pass"
        ? "translate(-140%, -40px) rotate(-24deg)"
        : "translate(0, -160%)"
    : `translate(${drag.x}px, ${drag.y}px) rotate(${drag.x * 0.05}deg)`;

  const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
  const likeOpacity = exit === "like" ? 1 : clamp01(drag.x / THRESHOLD);
  const passOpacity = exit === "pass" ? 1 : clamp01(-drag.x / THRESHOLD);
  const superOpacity = exit === "super_like" ? 1 : clamp01(-drag.y / THRESHOLD);

  return (
    <article
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      style={{
        transform,
        transition: dragging ? "none" : "transform 0.22s ease-out",
        touchAction: "none",
      }}
      className={cn(
        "relative rounded-2xl bg-surface shadow-card p-5 flex flex-col gap-4 select-none cursor-grab active:cursor-grabbing",
        className,
      )}
    >
      {/* Drag direction overlays */}
      <span
        style={{ opacity: likeOpacity }}
        className="pointer-events-none absolute top-6 right-6 z-10 rounded-lg border-2 border-primary px-3 py-1 text-lg font-extrabold tracking-wider text-primary rotate-12"
      >
        LIKE
      </span>
      <span
        style={{ opacity: passOpacity }}
        className="pointer-events-none absolute top-6 left-6 z-10 rounded-lg border-2 border-text-subtle px-3 py-1 text-lg font-extrabold tracking-wider text-text-subtle -rotate-12"
      >
        NOPE
      </span>
      <span
        style={{ opacity: superOpacity }}
        className="pointer-events-none absolute top-3 left-1/2 -translate-x-1/2 z-10 rounded-lg border-2 border-trust px-3 py-1 text-lg font-extrabold tracking-wider text-trust"
      >
        SUPER
      </span>

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

      <CompatibilityBar
        score={
          card.compatibilityScore <= 1
            ? card.compatibilityScore * 100
            : card.compatibilityScore
        }
      />

      {/* Action buttons (complement the drag gestures) */}
      <div
        className="flex items-center justify-center gap-5 pt-1"
        onPointerDown={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={() => commit("pass")}
          aria-label={`Pass ${card.displayName}`}
          className="grid place-items-center w-12 h-12 rounded-full bg-surface shadow-card text-text-subtle hover:text-text transition-colors active:scale-95"
        >
          <X className="w-6 h-6" strokeWidth={2} />
        </button>
        <button
          type="button"
          onClick={() => commit("super_like")}
          aria-label={`Super like ${card.displayName}`}
          className="grid place-items-center w-11 h-11 rounded-full bg-surface shadow-card text-trust hover:opacity-80 transition-opacity active:scale-95"
        >
          <Star className="w-5 h-5" strokeWidth={2} />
        </button>
        <button
          type="button"
          onClick={() => commit("like")}
          aria-label={`Like ${card.displayName}`}
          className="grid place-items-center w-12 h-12 rounded-full bg-primary text-primary-fg shadow-elevated hover:opacity-90 transition-opacity active:scale-95"
        >
          <Heart className="w-6 h-6" strokeWidth={2} />
        </button>
      </div>
    </article>
  );
}
