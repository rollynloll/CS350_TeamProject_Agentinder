import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useDiscover } from "@/api/endpoints/discover";
import { useAuth } from "@/store/auth";
import { EmptyState } from "@/design-system/components/EmptyState";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { DiscoverFilters } from "./components/DiscoverFilters";
import { DiscoverResultCard } from "./components/DiscoverResultCard";
import { SearchInput } from "./components/SearchInput";

export function DiscoverPage() {
  const { t } = useTranslation();
  const { activeAgentId } = useAuth();
  const query = useDiscover(activeAgentId ?? undefined);

  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  const needle = searchQuery.trim().toLowerCase();
  const cards = query.data?.cards;
  const filtered = useMemo(() => {
    if (!cards) return [];
    return cards.filter((card) => {
      const matchesText =
        !needle ||
        card.displayName.toLowerCase().includes(needle) ||
        card.bioSnippet.toLowerCase().includes(needle);
      const matchesTags =
        selectedTags.length === 0 ||
        selectedTags.every((tag) =>
          card.topTags.some(
            (cardTag) => cardTag.toLowerCase() === tag.toLowerCase(),
          ),
        );
      return matchesText && matchesTags;
    });
  }, [cards, needle, selectedTags]);

  return (
    <>
      <MobileHeader title={t("discover.title")} />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-4 space-y-4">
        <DiscoverFilters selected={selectedTags} onChange={setSelectedTags} />
        <QueryBoundary query={query}>
          {() =>
            filtered.length === 0 ? (
              <EmptyState
                title="No matches"
                description="Try removing tag filters or a different keyword."
              />
            ) : (
              <div className="space-y-3">
                {filtered.map((card) => (
                  <DiscoverResultCard key={card.agentId} card={card} />
                ))}
              </div>
            )
          }
        </QueryBoundary>
      </div>
      <SearchInput value={searchQuery} onChange={setSearchQuery} />
    </>
  );
}
