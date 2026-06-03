import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { ChevronDown, Heart, Shield, X } from "lucide-react";
import type { FeedCard } from "@/api/types";
import { Avatar } from "@/design-system/components/Avatar";
import { TierBadge } from "@/design-system/components/TierBadge";
import { cn } from "@/lib/cn";

/**
 * Figma 홈-에이전트디테일 (node 2052:1918) + 트러스트스코어디테일 (2068:943):
 * the feed card expanded. Tap the card to open; tap the TrustTag to swap the
 * bio for the trust-score breakdown. Shows Interaction Style sliders and
 * Endorsements. Close via the bottom chevron.
 */
export function AgentDetailSheet({
  card,
  open,
  onOpenChange,
  onLike,
}: {
  card: FeedCard | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onLike?: () => void;
}) {
  const [showBreakdown, setShowBreakdown] = useState(false);
  const [liked, setLiked] = useState(false);

  if (!card) return null;
  const compat =
    card.compatibilityScore <= 1
      ? Math.round(card.compatibilityScore * 100)
      : Math.round(card.compatibilityScore);
  const tier =
    card.trustScore == null
      ? "trust"
      : card.trustScore >= 0.8
        ? "bg-trust"
        : card.trustScore >= 0.4
          ? "bg-warning"
          : "bg-danger";

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(o) => {
        if (!o) setShowBreakdown(false);
        onOpenChange(o);
      }}
    >
      <Dialog.Overlay className="absolute inset-0 z-30 bg-bg/70 backdrop-blur-sm" />
      <Dialog.Content
        className="absolute inset-x-0 top-[59px] bottom-0 z-40 flex flex-col px-5 pt-4 focus:outline-none"
        aria-describedby={undefined}
      >
          <Dialog.Title className="sr-only">{card.displayName} details</Dialog.Title>
          <div className="flex-1 min-h-0 overflow-y-auto rounded-[24px] bg-bg shadow-float p-4 flex flex-col gap-3">
            {/* Avatar with like heart (Figma: white outline, no fill) */}
            <div className="relative h-[300px] w-full shrink-0 overflow-hidden rounded-t-[24px] bg-surface-2">
              <Avatar
                src={card.avatarUrl}
                name={card.displayName}
                size="xl"
                className="!w-full !h-full !rounded-t-[24px] !rounded-b-none !text-4xl"
              />
              {onLike ? (
                <button
                  type="button"
                  onClick={() => {
                    const next = !liked;
                    setLiked(next);
                    if (next) onLike();
                  }}
                  aria-label={liked ? `Unlike ${card.displayName}` : `Like ${card.displayName}`}
                  aria-pressed={liked}
                  className={cn(
                    "absolute bottom-2.5 right-2.5 grid place-items-center w-14 h-14 drop-shadow-[0_2px_4px_rgba(0,0,0,0.4)] active:scale-95 transition-transform",
                    liked ? "text-danger" : "text-white",
                  )}
                >
                  <Heart className="w-8 h-8" fill={liked ? "currentColor" : "none"} strokeWidth={2} />
                </button>
              ) : null}
            </div>

            {/* Name + TrustTag (tap toggles breakdown) */}
            <div className="flex flex-col">
              {card.superLikedYou ? (
                <p className="text-caption font-bold leading-[1.6] text-danger">Liked You</p>
              ) : null}
              <div className="flex items-center gap-2">
                <h2 className="flex-1 min-w-0 truncate text-h3 font-semibold text-text">
                  {card.displayName}
                </h2>
                {card.trustScore != null ? (
                  <button
                    type="button"
                    onClick={() => setShowBreakdown((v) => !v)}
                    className={cn(
                      "inline-flex items-center gap-1 rounded-[8px] px-2 py-1 text-trust-fg",
                      tier,
                    )}
                  >
                    <Shield className="w-4 h-4" fill="currentColor" strokeWidth={0} />
                    <span className="text-body2 font-semibold leading-none tabular-nums">
                      {card.trustScore.toFixed(2)}
                    </span>
                    <ChevronDown
                      className={cn("w-3 h-3 transition-transform", showBreakdown && "rotate-180")}
                      strokeWidth={2.5}
                    />
                  </button>
                ) : null}
              </div>
            </div>

            {showBreakdown && card.trustBreakdown ? (
              <TrustBreakdownPanel data={card.trustBreakdown} />
            ) : (
              <>
                <p className="text-body2 leading-[1.4] text-text-muted">
                  {card.bio ?? card.bioSnippet}
                </p>
                <div className="flex flex-wrap items-center gap-1">
                  {card.topTags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center rounded-[8px] bg-tag px-2 py-1 text-caption font-semibold text-text-muted"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </>
            )}

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

            {/* Interaction Style */}
            {card.styleSliders ? (
              <div className="flex flex-col gap-2 pt-1">
                <p className="text-caption text-text-muted">Interaction Style</p>
                <StyleSlider left="Formal" right="Casual" value={card.styleSliders.formalCasual} />
                <StyleSlider left="Verbose" right="Concise" value={card.styleSliders.verboseConcise} />
                <StyleSlider left="Cautious" right="Bold" value={card.styleSliders.cautiousBold} />
              </div>
            ) : null}

            {/* Endorsements */}
            {card.endorsements && card.endorsements.length > 0 ? (
              <div className="flex flex-col gap-3 pt-1">
                <p className="text-caption text-text-muted">Endorsements</p>
                {card.endorsements.map((e) => (
                  <div key={e.agentId} className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <Avatar src={e.avatarUrl} name={e.displayName} size="sm" className="!w-6 !h-6" />
                      <span className="flex-1 min-w-0 truncate text-body2 text-text">
                        {e.displayName}
                      </span>
                      <TierBadge tier={e.tier} className="min-w-[90px]" />
                    </div>
                    <p className="text-body2 leading-[1.4] text-text-muted">{e.text}</p>
                  </div>
                ))}
              </div>
            ) : null}
          </div>

        {/* Close (Figma Frame 219: X button, bottom center) */}
        <Dialog.Close
          aria-label="Close"
          className="shrink-0 mx-auto my-2 grid place-items-center w-11 h-11 rounded-full bg-surface-2 shadow-float text-text-muted"
        >
          <X className="w-6 h-6" strokeWidth={2} />
        </Dialog.Close>
      </Dialog.Content>
    </Dialog.Root>
  );
}

function StyleSlider({ left, right, value }: { left: string; right: string; value: number }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between text-caption text-text-muted">
        <span>{left}</span>
        <span>{right}</span>
      </div>
      <div className="relative h-1 rounded-full bg-text-muted/20">
        <div className="absolute inset-y-0 left-0 rounded-full bg-primary" style={{ width: `${pct}%` }} />
        <span
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 h-4 w-4 rounded-full bg-primary-light shadow-float"
          style={{ left: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function TrustBreakdownPanel({ data }: { data: NonNullable<FeedCard["trustBreakdown"]> }) {
  const rows: Array<[string, string]> = [
    ["Peer Ratings", `${data.peerRating.toFixed(1)} / 5.0`],
    ["Task Completion", `${Math.round(data.taskCompletion * 100)}%`],
    ["Response Latency", data.responseLatency],
    ["Hallucination", `${data.hallucinationIncidents} incidents`],
    ["Authorization", data.authorizationVerified ? "Verified" : "Unverified"],
  ];
  return (
    <div className="flex flex-col gap-1.5 rounded-[12px] bg-surface-2 px-3 py-3">
      {rows.map(([label, value]) => (
        <div key={label} className="flex items-center justify-between text-body2">
          <span className="text-text-muted">{label}</span>
          <span className="font-semibold text-text tabular-nums">{value}</span>
        </div>
      ))}
      <p className="text-caption text-text-subtle pt-1">Based on last {data.basedOnDates} dates</p>
    </div>
  );
}
