import { Link, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAgentProfile } from "@/api/endpoints/agents";
import { Avatar } from "@/design-system/components/Avatar";
import { Badge } from "@/design-system/components/Badge";
import { Button } from "@/design-system/components/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/design-system/components/Card";
import { PageHeader } from "@/design-system/components/PageHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { TrustBadge } from "@/design-system/components/TrustBadge";

export function AgentDetailPage() {
  const { t } = useTranslation();
  const { agentId } = useParams<{ agentId: string }>();
  const query = useAgentProfile(agentId);

  return (
    <>
      <QueryBoundary query={query}>
        {(profile) => (
          <>
            <PageHeader
              title={profile.displayName}
              description={profile.bio.slice(0, 120)}
              action={
                <Button asChild size="sm">
                  <Link to={`/agents/${profile.agentId}/edit`}>{t("common.edit")}</Link>
                </Button>
              }
            />
            <div className="grid gap-4 md:grid-cols-3">
              <Card className="md:col-span-1">
                <CardBody className="flex flex-col items-center text-center gap-3">
                  <Avatar src={profile.avatarUrl} name={profile.displayName} size="xl" />
                  <TrustBadge score={profile.trustScore} />
                  <Badge tone="info">{profile.visibility}</Badge>
                </CardBody>
              </Card>
              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle>Capabilities</CardTitle>
                </CardHeader>
                <CardBody className="flex flex-wrap gap-2">
                  {profile.capabilityTags.map((tag) => (
                    <Badge key={tag}>{tag}</Badge>
                  ))}
                </CardBody>
              </Card>
            </div>
            <p className="text-xs text-text-muted mt-4">{t("common.scaffold_notice")}</p>
          </>
        )}
      </QueryBoundary>
    </>
  );
}
