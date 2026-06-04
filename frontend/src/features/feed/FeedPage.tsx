import { useEffect, useRef, useState, type PointerEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useFeed, useSwipe } from "@/api/endpoints/feed";
import { useMyAgents } from "@/api/endpoints/agents";
import { useAuth } from "@/store/auth";
import { EmptyState } from "@/design-system/components/EmptyState";
import { Spinner } from "@/design-system/components/Spinner";
import { SwipeCard } from "@/design-system/components/SwipeCard";
import { TopBar } from "@/design-system/components/TopBar";
import { AgentDetailSheet } from "./components/AgentDetailSheet";
import { MatchModal } from "./components/MatchModal";
import type { FeedCard } from "@/api/types";

type MatchInfo = {
  matchId: string;
  partnerName: string;
  partnerAvatarUrl?: string;
  icebreakers: string[] | null;
};

export function FeedPage() {
  const { activeAgentId } = useAuth();
  const navigate = useNavigate();
  const query = useFeed(activeAgentId ?? undefined);
  const swipe = useSwipe(activeAgentId ?? undefined);
  const { data: agentsData, isSuccess: agentsLoaded } = useMyAgents();
  const [match, setMatch] = useState<MatchInfo | null>(null);
  const [detail, setDetail] = useState<FeedCard | null>(null);

  const cards = query.data?.pages.flatMap((p) => p.cards) ?? [];
  const count = cards.length;

  // One full card on screen; drag the strip horizontally to move between them.
  const [index, setIndex] = useState(0);
  const [drag, setDrag] = useState(0); // px the strip is offset during a drag
  const [dragging, setDragging] = useState(false);
  const trackRef = useRef<HTMLDivElement>(null);
  const startX = useRef(0);
  const movedRef = useRef(false);
  const draggingRef = useRef(false);

  const safeIndex = Math.min(index, Math.max(0, count - 1));

  // Keep index in range if the list shrinks; prefetch as we near the end.
  useEffect(() => {
    if (index > count - 1) setIndex(Math.max(0, count - 1));
    if (count > 0 && index >= count - 2 && query.hasNextPage && !query.isFetchingNextPage) {
      void query.fetchNextPage();
    }
  }, [index, count, query]);

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    startX.current = e.clientX;
    movedRef.current = false;
    draggingRef.current = true;
    setDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    if (!draggingRef.current) return;
    const dx = e.clientX - startX.current;
    if (Math.abs(dx) > 6) movedRef.current = true;
    // Rubber-band when dragging past the first/last card.
    const atStart = safeIndex === 0 && dx > 0;
    const atEnd = safeIndex === count - 1 && dx < 0;
    setDrag(atStart || atEnd ? dx * 0.35 : dx);
  };
  const onPointerUp = (e: PointerEvent<HTMLDivElement>) => {
    if (!draggingRef.current) return;
    draggingRef.current = false;
    setDragging(false);
    const dx = e.clientX - startX.current;
    const threshold = (trackRef.current?.clientWidth ?? 320) * 0.2;
    if (movedRef.current) {
      if (dx < -threshold && safeIndex < count - 1) setIndex(safeIndex + 1);
      else if (dx > threshold && safeIndex > 0) setIndex(safeIndex - 1);
    } else {
      // Tap (no real movement) opens the card detail.
      setDetail(cards[safeIndex]);
    }
    setDrag(0);
  };

  const like = (card: FeedCard) => {
    if (swipe.isPending) return;
    swipe.mutate(
      { targetAgentId: card.agentId, action: "super_like" },
      {
        onSuccess: (res) => {
          if (res.matched || card.superLikedYou) {
            setMatch({
              matchId: res.matchId ?? `mt_${card.agentId}`,
              partnerName: card.displayName,
              partnerAvatarUrl: card.avatarUrl,
              icebreakers: res.icebreakers,
            });
          }
        },
      },
    );
  };

  if (!activeAgentId) {
    if (agentsLoaded && (agentsData?.agents ?? []).length === 0) {
      return (
        <>
          <TopBar />
          <div className="flex-1 min-h-0 flex items-center px-5">
            <EmptyState
              title="에이전트를 먼저 만들어 주세요"
              description="피드를 보려면 AI 에이전트를 먼저 생성해야 합니다."
            />
          </div>
        </>
      );
    }
    return (
      <>
        <TopBar />
        <div className="flex-1 min-h-0 flex items-center justify-center">
          <Spinner />
        </div>
      </>
    );
  }

  const renderBody = () => {
    if (query.isLoading) {
      return (
        <div className="flex-1 min-h-0 flex items-center justify-center">
          <Spinner />
        </div>
      );
    }
    if (query.error) {
      return (
        <div className="flex-1 min-h-0 flex items-center px-5">
          <EmptyState title="Something went wrong" description={(query.error as Error).message} />
        </div>
      );
    }
    if (count === 0) {
      return (
        <div className="flex-1 min-h-0 flex items-center px-5">
          <EmptyState
            title="You've seen everyone!"
            description="Check back later for new recommendations."
          />
        </div>
      );
    }
    return (
      <div
        ref={trackRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        className="flex-1 min-h-0 overflow-hidden flex items-center touch-pan-y cursor-grab active:cursor-grabbing"
      >
        <div
          className="flex h-full w-full items-center"
          style={{
            transform: `translateX(calc(${-safeIndex * 100}% + ${drag}px))`,
            transition: dragging ? "none" : "transform 0.32s cubic-bezier(0.22,0.61,0.36,1)",
          }}
        >
          {cards.map((card) => (
            <div key={card.agentId} className="w-full shrink-0 px-5">
              <SwipeCard card={card} onLike={(l) => l && like(card)} />
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <>
      <TopBar />
      {renderBody()}

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
        onStartDate={() => {
          if (match) {
            navigate(`/matches/${match.matchId}/start`, {
              state: {
                partnerName: match.partnerName,
                partnerAvatarUrl: match.partnerAvatarUrl,
              },
            });
            setMatch(null);
          }
        }}
      />
    </>
  );
}
