import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { useAnalytics } from "@/api/endpoints/analytics";
import { useAuth } from "@/store/auth";
import { Avatar } from "@/design-system/components/Avatar";
import { CompatibilityBar } from "@/design-system/components/CompatibilityBar";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { TierBadge } from "@/design-system/components/TierBadge";
import { TrustBadge } from "@/design-system/components/TrustBadge";
import type { AnalyticsResponse, Tier } from "@/api/types";

const tierFill: Record<Tier, string> = {
  stranger: "var(--color-tier-stranger)",
  acquaintance: "var(--color-tier-acquaintance)",
  colleague: "var(--color-tier-colleague)",
  trusted_partner: "var(--color-tier-trusted)",
};

export function AnalyticsPage() {
  const { t } = useTranslation();
  const { activeAgentId } = useAuth();
  const query = useAnalytics(activeAgentId ?? undefined);

  return (
    <>
      <MobileHeader showBack title={t("analytics.title")} />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-4">
        <QueryBoundary query={query}>
          {(data) => (
            <>
              <TrustScoreCard data={data} />
              <DateSuccessCard data={data} />
              <TopCapabilitiesCard data={data} />
              <RelationshipTierCard data={data} />
              <BestPartnerCard data={data} />
            </>
          )}
        </QueryBoundary>
      </div>
    </>
  );
}

function SectionCard({
  title,
  meta,
  children,
}: {
  title: string;
  meta?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl bg-surface shadow-card p-4 space-y-3">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-text">{title}</h2>
        {meta ? <span className="text-[11px] text-text-subtle">{meta}</span> : null}
      </div>
      {children}
    </section>
  );
}

function TrustScoreCard({ data }: { data: AnalyticsResponse }) {
  const series = data.trustScoreTrend.map((p) => ({
    label: p.date.slice(5),
    score: Math.round(p.score * 100),
  }));
  const range =
    series.length > 0
      ? `${series[0].label} ~ ${series[series.length - 1].label}`
      : undefined;
  return (
    <SectionCard title="Trust Score" meta={range}>
      <div className="h-32">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={series}>
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              stroke="var(--color-text-subtle)"
              fontSize={10}
            />
            <YAxis hide domain={[0, 100]} />
            <Bar
              dataKey="score"
              fill="var(--color-primary)"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

function DateSuccessCard({ data }: { data: AnalyticsResponse }) {
  const success = Math.round(data.dateStats.successRate * 100);
  const fail = 100 - success;
  const pieData = [
    { name: "Success", value: success, fill: "var(--color-trust)" },
    { name: "Fail", value: fail, fill: "var(--color-danger-light)" },
  ];
  const successCount = Math.round(
    data.dateStats.totalDates * data.dateStats.successRate,
  );
  return (
    <SectionCard title="Date Success">
      <div className="flex items-center gap-4">
        <div className="w-28 h-28 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                dataKey="value"
                innerRadius={28}
                outerRadius={48}
                startAngle={90}
                endAngle={-270}
                strokeWidth={0}
              >
                {pieData.map((d) => (
                  <Cell key={d.name} fill={d.fill} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm tabular-nums flex-1">
          <dt className="text-text-muted">Total</dt>
          <dd className="text-right font-semibold">{data.dateStats.totalDates}</dd>
          <dt className="text-text-muted">Success</dt>
          <dd className="text-right font-semibold">{successCount}</dd>
          <dt className="text-text-muted">Fail</dt>
          <dd className="text-right font-semibold">
            {data.dateStats.totalDates - successCount}
          </dd>
          <dt className="text-text-muted">Rate</dt>
          <dd className="text-right font-semibold text-primary">{success}%</dd>
        </dl>
      </div>
    </SectionCard>
  );
}

function TopCapabilitiesCard({ data }: { data: AnalyticsResponse }) {
  return (
    <SectionCard title="Most Compatible capability">
      <div className="grid grid-cols-3 gap-2">
        {data.compatibilityBreakdown.topDomains.slice(0, 3).map((d) => (
          <div
            key={d.domain}
            className="rounded-xl bg-surface-2 px-2 py-3 text-center"
          >
            <div className="text-sm font-semibold text-text capitalize truncate">
              {d.domain.replace(/_/g, " ")}
            </div>
            <div className="text-[11px] text-text-muted mt-0.5 tabular-nums">
              {Math.round(d.avgScore * 100)}%
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

function RelationshipTierCard({ data }: { data: AnalyticsResponse }) {
  const series = data.relationshipGrowth.map((row) => ({
    label: row.date.slice(5),
    stranger: row.stranger,
    acquaintance: row.acquaintance,
    colleague: row.colleague,
    trusted_partner: row.trusted_partner,
  }));
  return (
    <SectionCard title="Relationship Tier">
      <div className="h-36">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={series}>
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              stroke="var(--color-text-subtle)"
              fontSize={10}
            />
            <YAxis hide />
            <Bar dataKey="stranger" stackId="a" fill={tierFill.stranger} />
            <Bar dataKey="acquaintance" stackId="a" fill={tierFill.acquaintance} />
            <Bar dataKey="colleague" stackId="a" fill={tierFill.colleague} />
            <Bar
              dataKey="trusted_partner"
              stackId="a"
              fill={tierFill.trusted_partner}
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-wrap gap-3 text-[11px] text-text-muted">
        <Legend color={tierFill.stranger} label="Stranger" />
        <Legend color={tierFill.acquaintance} label="Acquaintance" />
        <Legend color={tierFill.colleague} label="Colleague" />
        <Legend color={tierFill.trusted_partner} label="Trusted" />
      </div>
    </SectionCard>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span
        className="inline-block w-2.5 h-2.5 rounded-sm"
        style={{ backgroundColor: color }}
      />
      {label}
    </span>
  );
}

function BestPartnerCard({ data }: { data: AnalyticsResponse }) {
  const best = data.relationshipSummary.recentActivity[0];
  if (!best) return null;
  return (
    <SectionCard title="Best partner">
      <article className="rounded-xl bg-surface-2 p-3 flex flex-col gap-3">
        <TierBadge tier={best.tier} />
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <Avatar
              src={best.partnerAvatarUrl}
              name={best.partnerDisplayName}
              size="lg"
            />
            <div className="font-bold text-base truncate">
              {best.partnerDisplayName}
            </div>
          </div>
          <TrustBadge score={0.7} />
        </div>
        <CompatibilityBar score={88} />
        <div className="grid grid-cols-1 gap-2 text-[11px]">
          <div>
            <div className="text-text-muted">Interaction frequencies</div>
            <div className="text-text">
              {best.mutualRating
                ? `${(best.mutualRating * 10).toFixed(0)} interactions / week`
                : "—"}
            </div>
          </div>
          <div>
            <div className="text-text-muted">Mutual ratings</div>
            <div className="text-text tabular-nums">
              ★ {best.mutualRating.toFixed(1)} / 5
            </div>
          </div>
        </div>
      </article>
    </SectionCard>
  );
}
