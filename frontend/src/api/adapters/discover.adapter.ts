import type { DiscoverFilters, DiscoverResponse } from "../types";
import type { BeDiscoverResponse } from "./backend-types";
import { mapFeedCard } from "./feed.adapter";

const FILTER_KEY_MAP: Record<string, keyof DiscoverFilters> = {
  q: "q",
  capability: "capability",
  trustMin: "trustMin",
  trustMax: "trustMax",
  trust_min: "trustMin",
  trust_max: "trustMax",
  style: "style",
  domain: "domain",
  availability: "availability",
};

export function mapDiscoverResponse(be: BeDiscoverResponse): DiscoverResponse {
  const cards = (be.items ?? []).map(mapFeedCard);
  const applied: Partial<DiscoverFilters> = {};
  for (const [k, v] of Object.entries(be.applied_filters ?? {})) {
    const mapped = FILTER_KEY_MAP[k];
    if (mapped) (applied as Record<string, unknown>)[mapped] = v;
  }
  return {
    cards,
    appliedFilters: applied,
    totalResults: cards.length,
  };
}
