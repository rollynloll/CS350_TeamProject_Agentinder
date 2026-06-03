import type { ReactNode } from "react";
import {
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { useAnalytics } from "@/api/endpoints/analytics";
import { useAuth } from "@/store/auth";
import { ProfileTabs } from "@/design-system/components/ProfileTabs";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { TopBar } from "@/design-system/components/TopBar";
import type { AnalyticsResponse } from "@/api/types";

/**
 * Figma profile-analytics tab (node 2054:1289): Week Summary (3 stats),
 * Trust Score Trend (line), Successful Date Rate (donut + counts), Top
 * Capability Area (3 stats). Each is a neumorphic float card.
 */
export function AnalyticsPage() {
  const { activeAgentId } = useAuth();
  const query = useAnalytics(activeAgentId ?? undefined);

  return (
    <>
      <TopBar />
      <ProfileTabs />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-4">
        <QueryBoundary query={query}>
          {(data) => (
            <>
              <WeekSummaryCard data={data} />
              <TrustTrendCard data={data} />
              <DateRateCard data={data} />
              <TopCapabilityCard data={data} />
            </>
          )}
        </QueryBoundary>
      </div>
    </>
  );
}

function Card({ title, meta, children }: { title: string; meta?: string; children: ReactNode }) {
  return (
    <section className="rounded-[12px] bg-bg shadow-float px-3 py-2 space-y-3">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-h3 font-semibold text-text">{title}</h2>
        {meta ? <span className="text-caption text-text-subtle">{meta}</span> : null}
      </div>
      {children}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex-1 min-w-0">
      <p className="text-caption text-text-muted truncate">{label}</p>
      <p className="text-display font-semibold text-text tabular-nums leading-tight">{value}</p>
    </div>
  );
}

function WeekSummaryCard({ data }: { data: AnalyticsResponse }) {
  const ratings = data.relationshipSummary.recentActivity.map((a) => a.mutualRating);
  const avgRating = ratings.length
    ? (ratings.reduce((s, r) => s + r, 0) / ratings.length).toFixed(1)
    : "—";
  return (
    <Card title="Week Summary">
      <div className="flex gap-2">
        <Stat label="Date Count" value={data.dateStats.totalDates} />
        <Stat label="New Match" value={data.relationshipSummary.totalRelationships} />
        <Stat label="Avg Rating" value={avgRating} />
      </div>
    </Card>
  );
}

function TrustTrendCard({ data }: { data: AnalyticsResponse }) {
  const series = data.trustScoreTrend.map((p) => ({
    label: p.date.slice(5),
    score: Number(p.score.toFixed(2)),
  }));
  const today = series.length ? series[series.length - 1].score.toFixed(2) : "—";
  return (
    <Card title="Trust Score Trend" meta={`Today ${today}`}>
      <div className="h-28">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              stroke="var(--color-text-subtle)"
              fontSize={10}
              interval="preserveStartEnd"
            />
            <YAxis hide domain={[0, 1]} />
            <Line
              type="monotone"
              dataKey="score"
              stroke="var(--color-primary)"
              strokeWidth={2.5}
              dot={{ r: 3, fill: "var(--color-primary)", strokeWidth: 0 }}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function DateRateCard({ data }: { data: AnalyticsResponse }) {
  const rate = Math.round(data.dateStats.successRate * 100);
  const total = data.dateStats.totalDates;
  const success = Math.round(total * data.dateStats.successRate);
  const pie = [
    { name: "Success", value: rate, fill: "var(--color-primary)" },
    { name: "Rest", value: 100 - rate, fill: "var(--color-surface-2)" },
  ];
  return (
    <Card title="Successful Date Rate">
      <div className="flex items-center gap-4">
        <div className="relative w-40 h-40 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pie}
                dataKey="value"
                innerRadius={56}
                outerRadius={72}
                startAngle={90}
                endAngle={-270}
                strokeWidth={0}
              >
                {pie.map((d) => (
                  <Cell key={d.name} fill={d.fill} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <span className="absolute inset-0 grid place-items-center text-display font-semibold text-text tabular-nums">
            {rate}%
          </span>
        </div>
        <div className="flex flex-col gap-4">
          <div>
            <p className="text-body2 text-text-muted">Total Dates</p>
            <p className="text-display font-semibold text-text tabular-nums leading-tight">
              {total}
            </p>
          </div>
          <div>
            <p className="text-body2 text-text-muted">Success</p>
            <p className="text-display font-semibold text-text tabular-nums leading-tight">
              {success}
            </p>
          </div>
        </div>
      </div>
    </Card>
  );
}

function TopCapabilityCard({ data }: { data: AnalyticsResponse }) {
  return (
    <Card title="Top Capability Area">
      <div className="flex gap-2">
        {data.compatibilityBreakdown.topDomains.slice(0, 3).map((d) => (
          <div key={d.domain} className="flex-1 min-w-0">
            <p className="text-body1 font-semibold text-text capitalize truncate">
              {d.domain.replace(/_/g, " ")}
            </p>
            <p className="text-display font-semibold text-primary tabular-nums leading-tight">
              {Math.round(d.avgScore * 100)}%
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}
