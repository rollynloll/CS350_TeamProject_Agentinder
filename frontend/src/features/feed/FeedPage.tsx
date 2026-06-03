import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useFeed, useSwipe } from "@/api/endpoints/feed";
import { useAuth } from "@/store/auth";
import { EmptyState } from "@/design-system/components/EmptyState";
import { PageScroll } from "@/design-system/components/PageScroll";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { SwipeCard } from "@/design-system/components/SwipeCard";
import { MatchModal } from "./components/MatchModal";

type MatchInfo = { matchId: string; partnerName: string; icebreakers: string[] | null };

export function FeedPage() {
  const { activeAgentId } = useAuth();
  const navigate = useNavigate();
  const query = useFeed(activeAgentId ?? undefined);
  const swipe = useSwipe(activeAgentId ?? undefined);
  const [match, setMatch] = useState<MatchInfo | null>(null);

  return (
    <>
      <PageScroll>
        <QueryBoundary query={query}>
          {(data) => {
            const card = data.cards[0];
            if (!card) {
              return (
                <EmptyState
                  title="You've seen everyone!"
                  description="Check back later for new recommendations."
                />
              );
            }
            return (
              <SwipeCard
                key={card.agentId}
                card={card}
                onSwipe={(action) => {
                  if (swipe.isPending) return;
                  swipe.mutate(
                    { targetAgentId: card.agentId, action },
                    {
                      onSuccess: (res) => {
                        if (res.matched && res.matchId) {
                          setMatch({
                            matchId: res.matchId,
                            partnerName: card.displayName,
                            icebreakers: res.icebreakers,
                          });
                        }
                      },
                    },
                  );
                }}
              />
            );
          }}
        </QueryBoundary>
      </PageScroll>

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
