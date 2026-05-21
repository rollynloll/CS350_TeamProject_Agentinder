import { useFeed } from "@/api/endpoints/feed";
import { useAuth } from "@/store/auth";
import { EmptyState } from "@/design-system/components/EmptyState";
import { PageScroll } from "@/design-system/components/PageScroll";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { SwipeCard } from "@/design-system/components/SwipeCard";

export function FeedPage() {
  const { activeAgentId } = useAuth();
  const query = useFeed(activeAgentId ?? undefined);

  return (
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
          return <SwipeCard card={card} />;
        }}
      </QueryBoundary>
    </PageScroll>
  );
}
