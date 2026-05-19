import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMyAgents } from "@/api/endpoints/agents";
import { Avatar } from "@/design-system/components/Avatar";
import { Button } from "@/design-system/components/Button";
import { Card, CardBody } from "@/design-system/components/Card";
import { PageHeader } from "@/design-system/components/PageHeader";
import { PageScroll } from "@/design-system/components/PageScroll";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { TrustBadge } from "@/design-system/components/TrustBadge";

export function MyAgentsPage() {
  const { t } = useTranslation();
  const query = useMyAgents();

  return (
    <PageScroll>
      <PageHeader
        title={t("agents.title")}
        description={t("agents.description")}
        action={
          <Button asChild size="sm">
            <Link to="/agents/new">{t("agents.new")}</Link>
          </Button>
        }
      />
      <QueryBoundary query={query}>
        {(data) => (
          <div className="grid gap-3 md:grid-cols-2">
            {data.agents.map((agent) => (
              <Card key={agent.agentId}>
                <CardBody className="flex items-start gap-3">
                  <Avatar src={agent.avatarUrl} name={agent.displayName} size="lg" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <Link
                        to={`/agents/${agent.agentId}`}
                        className="font-semibold hover:underline truncate"
                      >
                        {agent.displayName}
                      </Link>
                      <TrustBadge score={agent.trustScore} />
                    </div>
                    <p className="text-sm text-text-muted mt-1 line-clamp-2">
                      {agent.bioSnippet}
                    </p>
                    <div className="text-xs text-text-muted mt-2 flex gap-3">
                      <span>{agent.activeMatchCount} active matches</span>
                      <span>{Math.round(agent.profileCompleteness * 100)}% complete</span>
                    </div>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </QueryBoundary>
    </PageScroll>
  );
}
