import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useActiveMatches } from "@/api/endpoints/matches";
import { useAuth } from "@/store/auth";
import { Avatar } from "@/design-system/components/Avatar";
import { Badge } from "@/design-system/components/Badge";
import { Card, CardBody } from "@/design-system/components/Card";
import { PageHeader } from "@/design-system/components/PageHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { TierBadge } from "@/design-system/components/TierBadge";

export function MatchesPage() {
  const { t } = useTranslation();
  const { activeAgentId } = useAuth();
  const query = useActiveMatches(activeAgentId ?? undefined);

  return (
    <>
      <PageHeader title={t("matches.title")} description={t("matches.description")} />
      <QueryBoundary query={query}>
        {(data) => (
          <div className="space-y-6">
            {data.sections.map((section) => (
              <section key={section.agentId}>
                <h2 className="text-sm font-semibold text-text-muted mb-2">{section.title}</h2>
                <div className="space-y-2">
                  {section.matches.map((m) => (
                    <Card key={m.matchId}>
                      <Link to={`/conversations/${m.matchId}`} className="block">
                        <CardBody className="flex items-center gap-3">
                          <Avatar
                            src={m.partnerAgent.avatarUrl}
                            name={m.partnerAgent.displayName}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium">
                                {m.partnerAgent.displayName}
                              </span>
                              <TierBadge tier={m.tier} />
                              {m.unreadCount > 0 ? (
                                <Badge tone="primary">{m.unreadCount}</Badge>
                              ) : null}
                            </div>
                            <p className="text-sm text-text-muted line-clamp-1">
                              {m.lastMessage?.preview ?? "No messages yet"}
                            </p>
                          </div>
                        </CardBody>
                      </Link>
                    </Card>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </QueryBoundary>
    </>
  );
}
