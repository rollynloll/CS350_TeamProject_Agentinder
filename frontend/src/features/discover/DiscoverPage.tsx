import { useTranslation } from "react-i18next";
import { useDiscover } from "@/api/endpoints/discover";
import { useAuth } from "@/store/auth";
import { PageHeader } from "@/design-system/components/PageHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { SwipeCard } from "@/design-system/components/SwipeCard";

export function DiscoverPage() {
  const { t } = useTranslation();
  const { activeAgentId } = useAuth();
  const query = useDiscover(activeAgentId ?? undefined);

  return (
    <>
      <PageHeader title={t("discover.title")} description={t("discover.description")} />
      <QueryBoundary query={query}>
        {(data) => (
          <>
            <div className="text-sm text-text-muted mb-3">
              Total results: {data.totalResults}
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.cards.map((card) => (
                <SwipeCard key={card.agentId} card={card} />
              ))}
            </div>
          </>
        )}
      </QueryBoundary>
      <p className="text-xs text-text-muted mt-4">{t("common.scaffold_notice")}</p>
    </>
  );
}
