import { useEffect, useRef, useState } from "react";
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

type MatchInfo = { matchId: string; partnerName: string; icebreakers: string[] | null };

// Carousel sizing — main card ~85% of the shell, leaving ~7.5% peek on each side.
// Mobile: vw (shell fills viewport). Desktop: fixed pixels (shell is 393px).
const CARD_W = "w-[85vw] md:w-[334px]";
const EDGE_PAD = "px-[7.5vw] md:px-[29px]";
const SNAP_PAD = "scroll-pl-[7.5vw] scroll-pr-[7.5vw] md:scroll-pl-[29px] md:scroll-pr-[29px]";

export function FeedPage() {
  const { activeAgentId } = useAuth();
  const navigate = useNavigate();
  const query = useFeed(activeAgentId ?? undefined);
  const swipe = useSwipe(activeAgentId ?? undefined);
  const [match, setMatch] = useState<MatchInfo | null>(null);
  const [detail, setDetail] = useState<FeedCard | null>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);

  // activeAgentId 가 없으면 AuthedLayout 의 자동선택이 완료될 때까지 기다린다.
  // 에이전트가 아예 없는 경우는 생성 안내를 표시한다.
  const { data: agentsData, isSuccess: agentsLoaded } = useMyAgents();

  // Auto-fetch next page when the trailing sentinel scrolls into view.
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (
          entries[0]?.isIntersecting &&
          query.hasNextPage &&
          !query.isFetchingNextPage
        ) {
          void query.fetchNextPage();
        }
      },
      { threshold: 0.5 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [query]);

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
          <EmptyState
            title="Something went wrong"
            description={(query.error as Error).message}
          />
        </div>
      );
    }
    const cards = query.data?.pages.flatMap((p) => p.cards) ?? [];
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
    return (
      <div
        className={`flex-1 min-h-0 flex items-center overflow-x-auto overflow-y-hidden snap-x snap-mandatory scrollbar-hide ${SNAP_PAD}`}
      >
        <div className={`flex items-stretch gap-3 ${EDGE_PAD}`}>
          {cards.map((card) => (
            <div
              key={card.agentId}
              onClick={() => setDetail(card)}
              className={`shrink-0 snap-center cursor-pointer ${CARD_W}`}
            >
              <SwipeCard card={card} onLike={(l) => l && like(card)} />
            </div>
          ))}
          <div
            ref={sentinelRef}
            aria-hidden
            className="shrink-0 flex items-center justify-center w-12"
          >
            {query.isFetchingNextPage ? <Spinner /> : null}
          </div>
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
