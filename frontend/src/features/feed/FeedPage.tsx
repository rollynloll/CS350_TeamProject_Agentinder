import { useRef, useState, type PointerEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useFeed, useSwipe } from "@/api/endpoints/feed";
import { useAuth } from "@/store/auth";
import { EmptyState } from "@/design-system/components/EmptyState";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { SwipeCard } from "@/design-system/components/SwipeCard";
import { TopBar } from "@/design-system/components/TopBar";
import { AgentDetailSheet } from "./components/AgentDetailSheet";
import { MatchModal } from "./components/MatchModal";
import type { FeedCard } from "@/api/types";

type MatchInfo = { matchId: string; partnerName: string; icebreakers: string[] | null };

const THRESHOLD = 60; // px drag to flip to the adjacent card

export function FeedPage() {
  const { activeAgentId } = useAuth();
  const navigate = useNavigate();
  const query = useFeed(activeAgentId ?? undefined);
  const swipe = useSwipe(activeAgentId ?? undefined);
  const [match, setMatch] = useState<MatchInfo | null>(null);
  const [detail, setDetail] = useState<FeedCard | null>(null);

  // Horizontal filmstrip: all cards in a row, slid left/right by index.
  const [index, setIndex] = useState(0);
  const [drag, setDrag] = useState(0);
  const [dragging, setDragging] = useState(false);
  const start = useRef<{ x: number; y: number } | null>(null);
  const moved = useRef(false);

  const like = (card: FeedCard) => {
    if (swipe.isPending) return;
    swipe.mutate(
      { targetAgentId: card.agentId, action: "like" },
      {
        onSuccess: (res) => {
          // A "Liked You" agent already liked you back — liking always matches.
          if (card.superLikedYou) {
            setMatch({
              matchId: res.matchId ?? `mt_${card.agentId}`,
              partnerName: card.displayName,
              icebreakers: res.icebreakers,
            });
          }
        },
      },
    );
  };

  return (
    <>
      <TopBar />
      <QueryBoundary query={query}>
        {(data) => {
          const cards = data.cards;
          if (cards.length === 0) {
            return (
              <div className="flex-1 min-h-0 flex items-center px-5">
                <EmptyState
                  title="You've seen everyone!"
                  description="Check back later for new recommendations."
                />
              </div>
            );
          }

          const onDown = (e: PointerEvent<HTMLDivElement>) => {
            start.current = { x: e.clientX, y: e.clientY };
            moved.current = false;
            setDragging(true);
            e.currentTarget.setPointerCapture(e.pointerId);
          };
          const onMove = (e: PointerEvent<HTMLDivElement>) => {
            if (!start.current) return;
            const dx = e.clientX - start.current.x;
            if (Math.abs(dx) > 6) moved.current = true;
            setDrag(dx);
          };
          const onUp = (e: PointerEvent<HTMLDivElement>) => {
            if (!start.current) return;
            const dx = e.clientX - start.current.x;
            start.current = null;
            setDragging(false);
            setDrag(0);
            if (moved.current) {
              if (dx < -THRESHOLD && index < cards.length - 1) setIndex(index + 1);
              else if (dx > THRESHOLD && index > 0) setIndex(index - 1);
            } else {
              // Tap (no drag) → open the centered card's detail.
              const tappedHeart = (e.target as HTMLElement).closest("button[aria-pressed]");
              if (!tappedHeart) setDetail(cards[index]);
            }
          };

          return (
            <div className="flex-1 min-h-0 overflow-hidden flex items-center">
              <div
                onPointerDown={onDown}
                onPointerMove={onMove}
                onPointerUp={onUp}
                onPointerCancel={onUp}
                style={{
                  transform: `translateX(calc(${-index * 100}% + ${drag}px))`,
                  transition: dragging ? "none" : "transform 0.3s ease-out",
                  touchAction: "pan-y",
                }}
                className="flex w-full cursor-grab active:cursor-grabbing"
              >
                {cards.map((card) => (
                  <div key={card.agentId} className="w-full shrink-0 px-5">
                    <SwipeCard card={card} onLike={(l) => l && like(card)} />
                  </div>
                ))}
              </div>
            </div>
          );
        }}
      </QueryBoundary>

      <AgentDetailSheet
        card={detail}
        open={detail != null}
        onOpenChange={(o) => {
          if (!o) setDetail(null);
        }}
        onLike={() => {
          if (detail) like(detail);
        }}
      />

      <MatchModal
        open={match != null}
        onOpenChange={(o) => {
          if (!o) setMatch(null);
        }}
        partnerName={match?.partnerName ?? ""}
        icebreakers={match?.icebreakers}
        onMessage={() => {
          if (match) {
            navigate(`/conversations/${match.matchId}`);
            setMatch(null);
          }
        }}
      />
    </>
  );
}
