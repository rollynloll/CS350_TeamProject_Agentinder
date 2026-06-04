import { useQuery } from "@tanstack/react-query";
import { api } from "../client";
import type { AgentId, AnalyticsResponse, Tier } from "../types";
import { MIGRATE } from "../migration-flags";

export const analyticsKeys = {
  all: ["analytics"] as const,
  forAgent: (agentId: AgentId, period: string) => ["analytics", agentId, period] as const,
};

type BeAnalytics = {
  trustScoreTrend: Array<{ date: string; score: number }>;
  currentTrustScore: number | null;
  dateStats: {
    totalDates: number;
    successRate: number;
    avgStars: number;
    byType: Record<string, { count: number }>;
  };
  relationshipSummary: {
    totalRelationships: number;
    byTier: Record<string, number>;
  };
};

function mapBeAnalytics(be: BeAnalytics): AnalyticsResponse {
  const byTier = be.relationshipSummary.byTier;
  return {
    trustScoreTrend: be.trustScoreTrend,
    dateStats: {
      totalDates: be.dateStats.totalDates,
      successRate: be.dateStats.successRate,
      byType: {
        // DateType is unified to a single "date" kind; sum the backend's
        // legacy per-type counts into it.
        date: {
          count:
            (be.dateStats.byType.coffee_chat?.count ?? 0) +
            (be.dateStats.byType.deep_dive?.count ?? 0) +
            (be.dateStats.byType.activity_date?.count ?? 0),
          successRate: be.dateStats.successRate,
        },
      },
    },
    compatibilityBreakdown: {
      topDomains: [],
      styleMatchRate: 0,
    },
    relationshipGrowth: [],
    relationshipSummary: {
      totalRelationships: be.relationshipSummary.totalRelationships,
      byTier: {
        stranger: byTier.stranger ?? 0,
        acquaintance: byTier.acquaintance ?? 0,
        colleague: byTier.colleague ?? 0,
        trusted_partner: byTier.trusted_partner ?? 0,
      } as Record<Tier, number>,
      recentActivity: [],
    },
  };
}

export function useAnalytics(
  agentId: AgentId | undefined,
  period: "7d" | "30d" | "90d" | "all" = "30d",
) {
  return useQuery({
    queryKey: analyticsKeys.forAgent(agentId ?? "", period),
    queryFn: () =>
      MIGRATE.analytics
        ? api
            .get<BeAnalytics>(`/agents/${agentId}/analytics`, { query: { period } })
            .then(mapBeAnalytics)
        : api.get<AnalyticsResponse>(`/agents/${agentId}/analytics`, { query: { period } }),
    enabled: Boolean(agentId),
  });
}
