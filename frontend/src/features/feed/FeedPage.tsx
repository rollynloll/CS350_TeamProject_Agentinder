import { useTranslation } from "react-i18next";
import { useFeed } from "@/api/endpoints/feed";
import { useAuth } from "@/store/auth";
import { PageHeader } from "@/design-system/components/PageHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { SwipeCard } from "@/design-system/components/SwipeCard";
import { EmptyState } from "@/design-system/components/EmptyState";

export function FeedPage() {
  const { t } = useTranslation();
  const { activeAgentId } = useAuth();
  const query = useFeed(activeAgentId ?? undefined);

  return (
    <>
      <PageHeader title={t("feed.title")} description={t("feed.description")} />
      <QueryBoundary query={query}>
        {(data) =>
          data.cards.length === 0 ? (
            <EmptyState
              title="You've seen everyone!"
              description="Check back later for new recommendations."
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {data.cards.map((card) => (
                <SwipeCard key={card.agentId} card={card} />
              ))}
            </div>
          )
        }
      </QueryBoundary>
      <p className="text-xs text-text-muted mt-4">{t("common.scaffold_notice")}</p>
    </>
  );
}
