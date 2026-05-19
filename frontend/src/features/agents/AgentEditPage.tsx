import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAgentProfile } from "@/api/endpoints/agents";
import { PageHeader } from "@/design-system/components/PageHeader";
import { PageScroll } from "@/design-system/components/PageScroll";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { Card, CardBody } from "@/design-system/components/Card";

export function AgentEditPage() {
  const { t } = useTranslation();
  const { agentId } = useParams<{ agentId: string }>();
  const query = useAgentProfile(agentId);

  return (
    <PageScroll>
      <PageHeader title={t("agents.edit_title")} />
      <QueryBoundary query={query}>
        {(profile) => (
          <Card>
            <CardBody>
              <p className="text-sm text-text-muted">{t("common.scaffold_notice")}</p>
              <pre className="text-xs mt-3 bg-surface-2 p-3 rounded overflow-x-auto">
                {JSON.stringify(profile, null, 2)}
              </pre>
            </CardBody>
          </Card>
        )}
      </QueryBoundary>
    </PageScroll>
  );
}
