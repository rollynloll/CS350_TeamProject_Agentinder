import { useTranslation } from "react-i18next";
import { useRelationships } from "@/api/endpoints/relationships";
import { useAuth } from "@/store/auth";
import { Avatar } from "@/design-system/components/Avatar";
import { Card, CardBody } from "@/design-system/components/Card";
import { PageHeader } from "@/design-system/components/PageHeader";
import { PageScroll } from "@/design-system/components/PageScroll";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { TierBadge } from "@/design-system/components/TierBadge";

export function RelationshipsPage() {
  const { t } = useTranslation();
  const { activeAgentId } = useAuth();
  const query = useRelationships(activeAgentId ?? undefined);

  return (
    <PageScroll>
      <PageHeader
        title={t("relationships.title")}
        description={t("relationships.description")}
      />
      <QueryBoundary query={query}>
        {(data) => (
          <div className="space-y-6">
            {data.groups.map((group) => (
              <section key={group.tier}>
                <div className="flex items-center gap-2 mb-2">
                  <TierBadge tier={group.tier} />
                  <span className="text-sm text-text-muted">{group.count}</span>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {group.relationships.map((r) => (
                    <Card key={r.matchId}>
                      <CardBody className="flex items-center gap-3">
                        <Avatar
                          src={r.partnerAgent.avatarUrl}
                          name={r.partnerAgent.displayName}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate">
                            {r.partnerAgent.displayName}
                          </div>
                          <div className="text-xs text-text-muted">
                            {r.totalDates} dates · ★ {r.mutualRating.toFixed(1)}
                          </div>
                        </div>
                      </CardBody>
                    </Card>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </QueryBoundary>
    </PageScroll>
  );
}
