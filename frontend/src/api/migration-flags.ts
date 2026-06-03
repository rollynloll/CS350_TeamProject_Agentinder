// Per-endpoint migration flags: false = keep MSW mock, true = call the real
// FastAPI backend (with an adapter mapping the response to the frontend type).
//
// Each flag is driven by a VITE_MIGRATE_* env var (string "true"). Defaults to
// false so the app keeps running entirely on mocks with zero behaviour change.
// VITE_MIGRATE_ALL=true flips every endpoint on at once (handy for full E2E).
//
// When an endpoint is migrated, point VITE_API_BASE_URL at the real backend
// (e.g. http://localhost:8000/v1). Un-migrated endpoints are still served by
// MSW because their handlers register against the same base URL.

const on = (v: unknown): boolean => v === "true";

const ALL = on(import.meta.env.VITE_MIGRATE_ALL);
const flag = (v: unknown): boolean => ALL || on(v);

export const MIGRATE = {
  feed: flag(import.meta.env.VITE_MIGRATE_FEED),
  discover: flag(import.meta.env.VITE_MIGRATE_DISCOVER),
  swipe: flag(import.meta.env.VITE_MIGRATE_SWIPE),
  agentsList: flag(import.meta.env.VITE_MIGRATE_AGENTS_LIST),
  agentProfile: flag(import.meta.env.VITE_MIGRATE_AGENT_PROFILE),
  agentCreate: flag(import.meta.env.VITE_MIGRATE_AGENT_CREATE),
  agentUpdate: flag(import.meta.env.VITE_MIGRATE_AGENT_UPDATE),
  matches: flag(import.meta.env.VITE_MIGRATE_MATCHES),
  messages: flag(import.meta.env.VITE_MIGRATE_MESSAGES),
  dateHistory: flag(import.meta.env.VITE_MIGRATE_DATE_HISTORY),
  dateGet: flag(import.meta.env.VITE_MIGRATE_DATE_GET),
  dateSchedule: flag(import.meta.env.VITE_MIGRATE_DATE_SCHEDULE),
  dateEnd: flag(import.meta.env.VITE_MIGRATE_DATE_END),
} as const;

export type MigrationFlag = keyof typeof MIGRATE;
