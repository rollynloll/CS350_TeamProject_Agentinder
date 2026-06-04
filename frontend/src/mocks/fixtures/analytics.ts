import type { AnalyticsResponse, SettingsResponse } from "@/api/types";

// Deterministic per-agent multiplier (~0.6–1.3) so each profile's mock
// analytics / relationships look distinct but stable across reloads.
export function agentFactor(agentId: string): number {
  let h = 0;
  for (const ch of agentId) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return 0.6 + (h % 70) / 100;
}

const clamp01 = (n: number) => Math.max(0, Math.min(1, n));

export const analytics: AnalyticsResponse = {
  trustScoreTrend: [
    { date: "2026-04-01", score: 0.82 },
    { date: "2026-04-15", score: 0.87 },
    { date: "2026-05-01", score: 0.92 },
  ],
  dateStats: {
    totalDates: 18,
    successRate: 0.78,
    byType: {
      date: { count: 18, successRate: 0.78 },
    },
  },
  compatibilityBreakdown: {
    topDomains: [
      { domain: "research", avgScore: 0.91 },
      { domain: "writing", avgScore: 0.85 },
      { domain: "data_engineering", avgScore: 0.78 },
    ],
    styleMatchRate: 0.73,
  },
  relationshipGrowth: [
    { date: "2026-04-01", stranger: 10, acquaintance: 3, colleague: 1, trusted_partner: 0 },
    { date: "2026-05-01", stranger: 8, acquaintance: 5, colleague: 2, trusted_partner: 1 },
  ],
  relationshipSummary: {
    totalRelationships: 15,
    byTier: { stranger: 5, acquaintance: 6, colleague: 3, trusted_partner: 1 },
    recentActivity: [
      {
        matchId: "mt_seed_001",
        partnerDisplayName: "Scheduler",
        partnerAvatarUrl: "https://api.dicebear.com/9.x/bottts/svg?seed=Scheduler",
        tier: "acquaintance",
        lastInteractionAt: "2026-05-09T18:00:00Z",
        mutualRating: 4.2,
      },
    ],
  },
};

/** Per-agent variant of the analytics fixture. */
export function analyticsFor(agentId: string): AnalyticsResponse {
  const f = agentFactor(agentId);
  const c = structuredClone(analytics);
  c.trustScoreTrend = c.trustScoreTrend.map((p) => ({
    ...p,
    score: +clamp01(p.score * f).toFixed(2),
  }));
  c.dateStats.totalDates = Math.round(c.dateStats.totalDates * f);
  c.dateStats.successRate = +clamp01(c.dateStats.successRate * f).toFixed(2);
  c.dateStats.byType.date = {
    count: c.dateStats.totalDates,
    successRate: c.dateStats.successRate,
  };
  c.compatibilityBreakdown.topDomains = c.compatibilityBreakdown.topDomains.map((d) => ({
    ...d,
    avgScore: +clamp01(d.avgScore * f).toFixed(2),
  }));
  const t = c.relationshipSummary.byTier;
  t.stranger = Math.round(t.stranger * f);
  t.acquaintance = Math.round(t.acquaintance * f);
  t.colleague = Math.round(t.colleague * f);
  t.trusted_partner = Math.round(t.trusted_partner * f);
  c.relationshipSummary.totalRelationships =
    t.stranger + t.acquaintance + t.colleague + t.trusted_partner;
  return c;
}

export const settings: SettingsResponse = {
  account: {
    email: "user@example.com",
    displayName: "John Doe",
    createdAt: "2026-01-15T10:00:00Z",
  },
  apiKeys: [
    {
      keyId: "ak_001",
      name: "GPT-agent",
      lastUsedAt: "2026-05-09T18:00:00Z",
      createdAt: "2026-03-01T10:00:00Z",
    },
  ],
  notifications: {
    matchAlerts: true,
    dateReminders: true,
    weeklyDigest: true,
    messagePreview: true,
  },
  preferences: {
    globalTrustThreshold: 0.5,
    autoMatchRules: { enabled: false, minCompatibility: 0.8, minTrust: 0.7 },
  },
  privacy: {
    profileVisibility: "public",
    dateTranscriptSharing: "mutual_consent",
    analyticsOptIn: true,
  },
};
