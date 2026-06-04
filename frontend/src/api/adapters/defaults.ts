// Shared fillers for fields the backend does not (yet) expose, so adapters can
// produce complete frontend types without breaking the UI.

import type { DateType, InteractionStyle, Tier, Visibility } from "../types";

export const DEFAULT_INTERACTION_STYLE: InteractionStyle = {};

export function dicebearFallback(seed: string): string {
  return `https://api.dicebear.com/9.x/bottts/svg?seed=${encodeURIComponent(seed)}`;
}

export function avatarOrFallback(url: string | null | undefined, seed: string): string {
  return url && url.length > 0 ? url : dicebearFallback(seed);
}

export function normalizeVisibility(v: string | null | undefined): Visibility {
  const s = (v ?? "public").toLowerCase();
  if (s === "restricted" || s === "hidden") return s;
  return "public";
}

// Frontend FeedCard/AgentProfile use a "new_agent" | "verified" | string badge.
// Backend tier_badge is "new_agent" or a numeric date-count string.
export function trustBadgeFrom(tierBadge: string | null | undefined): string {
  return tierBadge === "new_agent" || !tierBadge ? "new_agent" : "verified";
}

const TIER_VALUES: Tier[] = ["stranger", "acquaintance", "colleague", "trusted_partner"];
export function normalizeTier(v: string | null | undefined): Tier {
  const s = (v ?? "stranger").toLowerCase();
  return (TIER_VALUES as string[]).includes(s) ? (s as Tier) : "stranger";
}

// Date kinds were unified into a single "Date"; any backend value maps to it.
export function normalizeDateType(_v?: string | null): DateType {
  return "date";
}

// Placeholder partner label until matches/messages endpoints join partner profiles.
export function partnerLabel(agentId: string): string {
  return `Agent ${agentId.slice(0, 4)}`;
}

export function nowIso(): string {
  return new Date().toISOString();
}
