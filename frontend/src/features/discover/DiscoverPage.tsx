import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useDiscover } from "@/api/endpoints/discover";
import { useSwipe } from "@/api/endpoints/feed";
import { useAuth } from "@/store/auth";
import { EmptyState } from "@/design-system/components/EmptyState";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { TopBar } from "@/design-system/components/TopBar";
import { AgentDetailSheet } from "@/features/feed/components/AgentDetailSheet";
import { DiscoverResultCard } from "./components/DiscoverResultCard";
import { SearchInput } from "./components/SearchInput";
import type { FeedCard } from "@/api/types";

export function DiscoverPage() {
  const { t } = useTranslation();
  const { activeAgentId } = useAuth();
  const query = useDiscover(activeAgentId ?? undefined);
  const swipe = useSwipe(activeAgentId ?? undefined);

  const [searchQuery, setSearchQuery] = useState("");
  const [detail, setDetail] = useState<FeedCard | null>(null);

  const needle = searchQuery.trim().toLowerCase();
  const cards = query.data?.cards;
  const filtered = useMemo(() => {
    if (!cards) return [];
    return cards.filter(
      (card) =>
        !needle ||
        card.displayName.toLowerCase().includes(needle) ||
        card.bioSnippet.toLowerCase().includes(needle),
    );
  }, [cards, needle]);

  return (
    <>
      <TopBar />
      <div className="flex-1 min-h-0 overflow-y-auto px-3 pt-2 pb-4 space-y-3">
        <QueryBoundary query={query}>
          {() =>
            filtered.length === 0 ? (
              <EmptyState title="No matches" description="Try a different keyword." />
            ) : (
              <div className="space-y-3">
                {filtered.map((card) => (
                  <DiscoverResultCard
                    key={card.agentId}
                    card={card}
                    onOpen={() => setDetail(card)}
                  />
                ))}
              </div>
            )
          }
        </QueryBoundary>
      </div>
      <SearchInput
        value={searchQuery}
        onChange={setSearchQuery}
        placeholder={t("discover.search_placeholder", {
          defaultValue: "Search for your partner.",
        })}
      />

      <AgentDetailSheet
        card={detail}
        open={detail != null}
        onOpenChange={(o) => {
          if (!o) setDetail(null);
        }}
        onLike={() => {
          if (detail && !swipe.isPending) {
            swipe.mutate({ targetAgentId: detail.agentId, action: "like" });
          }
        }}
      />
    </>
  );
}
