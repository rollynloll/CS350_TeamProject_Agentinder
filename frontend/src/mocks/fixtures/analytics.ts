import type { AnalyticsResponse, SettingsResponse } from "@/api/types";

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
      coffee_chat: { count: 12, successRate: 0.83 },
      activity_date: { count: 4, successRate: 0.75 },
      deep_dive: { count: 2, successRate: 0.5 },
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
        partnerDisplayName: "WriterBot",
        partnerAvatarUrl: "https://api.dicebear.com/9.x/bottts/svg?seed=WriterBot",
        tier: "acquaintance",
        lastInteractionAt: "2026-05-09T18:00:00Z",
        mutualRating: 4.2,
      },
    ],
  },
};

export const settings: SettingsResponse = {
  account: {
    email: "user@example.com",
    displayName: "John Doe",
    createdAt: "2026-01-15T10:00:00Z",
  },
  apiKeys: [
    {
      keyId: "ak_001",
      name: "Production",
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
