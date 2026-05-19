import { useTranslation } from "react-i18next";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAnalytics } from "@/api/endpoints/analytics";
import { useAuth } from "@/store/auth";
import { Card, CardBody, CardHeader, CardTitle } from "@/design-system/components/Card";
import { PageHeader } from "@/design-system/components/PageHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { TierBadge } from "@/design-system/components/TierBadge";

export function AnalyticsPage() {
  const { t } = useTranslation();
  const { activeAgentId } = useAuth();
  const query = useAnalytics(activeAgentId ?? undefined);

  return (
    <>
      <PageHeader title={t("analytics.title")} description={t("analytics.description")} />
      <QueryBoundary query={query}>
        {(data) => (
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Trust Score Trend</CardTitle>
              </CardHeader>
              <CardBody className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.trustScoreTrend}>
                    <CartesianGrid stroke="var(--color-border)" />
                    <XAxis dataKey="date" stroke="var(--color-text-muted)" />
                    <YAxis domain={[0, 1]} stroke="var(--color-text-muted)" />
                    <Tooltip />
                    <Line type="monotone" dataKey="score" stroke="var(--color-primary)" />
                  </LineChart>
                </ResponsiveContainer>
              </CardBody>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Date Outcomes</CardTitle>
              </CardHeader>
              <CardBody>
                <div className="text-3xl font-bold">{data.dateStats.totalDates}</div>
                <div className="text-sm text-text-muted">
                  Success rate {Math.round(data.dateStats.successRate * 100)}%
                </div>
              </CardBody>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Relationship Tiers</CardTitle>
              </CardHeader>
              <CardBody className="flex flex-wrap gap-2">
                {Object.entries(data.relationshipSummary.byTier).map(([tier, count]) => (
                  <div key={tier} className="flex items-center gap-2">
                    <TierBadge tier={tier as keyof typeof data.relationshipSummary.byTier} />
                    <span className="text-sm">{count}</span>
                  </div>
                ))}
              </CardBody>
            </Card>
          </div>
        )}
      </QueryBoundary>
    </>
  );
}
