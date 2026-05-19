import { useTranslation } from "react-i18next";
import { useDiscover } from "@/api/endpoints/discover";
import { useAuth } from "@/store/auth";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { DiscoverFilters } from "./components/DiscoverFilters";
import { DiscoverResultCard } from "./components/DiscoverResultCard";

export function DiscoverPage() {
  const { t } = useTranslation();
  const { activeAgentId } = useAuth();
  const query = useDiscover(activeAgentId ?? undefined);

  return (
    <>
      <MobileHeader title={t("discover.title")} />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-4">
        <DiscoverFilters />
        <QueryBoundary query={query}>
          {(data) => (
            <div className="space-y-3">
              {data.cards.map((card) => (
                <DiscoverResultCard key={card.agentId} card={card} />
              ))}
            </div>
          )}
        </QueryBoundary>
      </div>
    </>
  );
}
