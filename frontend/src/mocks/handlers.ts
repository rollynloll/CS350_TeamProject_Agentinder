import { http, HttpResponse } from "msw";
import type { Envelope } from "@/api/types";
import { uuid } from "@/lib/uuid";
import { agentProfiles, feedCards, myAgents } from "./fixtures/agents";
import { activeMatches, conversation, liveDate, matchDates, relationships } from "./fixtures/matches";
import { analytics, settings } from "./fixtures/analytics";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "https://api.agentinder.io/v1";

function ok<T>(data: T, paginationExtra?: Envelope<T>["meta"]) {
  const body: Envelope<T> = {
    data,
    meta: {
      requestId: uuid(),
      timestamp: new Date().toISOString(),
      ...paginationExtra,
    },
    error: null,
  };
  return HttpResponse.json(body);
}

function notFound(message = "Resource not found") {
  const body: Envelope<null> = {
    data: null,
    error: { code: "NOT_FOUND", message },
  };
  return HttpResponse.json(body, { status: 404 });
}

const url = (path: string): string => `${BASE}${path}`;

export const handlers = [
  // §3.1 Feed
  http.get(url("/feed/:agentId"), () => ok({ cards: feedCards })),
  http.post(url("/feed/:agentId/swipe"), async ({ request }) => {
    const body = (await request.json()) as { targetAgentId: string; action: string };
    const matched = body.action !== "pass" && Math.random() > 0.5;
    return ok({
      matched,
      matchId: matched ? `mt_${uuid().slice(0, 8)}` : null,
      icebreakers: matched
        ? ["You both list research as a capability. How do you verify sources?"]
        : null,
    });
  }),

  // §3.2 Discover
  http.get(url("/discover/:agentId"), ({ request }) => {
    const u = new URL(request.url);
    return ok({
      cards: feedCards,
      appliedFilters: {
        capability: u.searchParams.get("capability")?.split(",").filter(Boolean) ?? [],
        trustMin: Number(u.searchParams.get("trustMin") ?? 0) || undefined,
      },
      totalResults: feedCards.length,
    });
  }),

  // §3.3 My Profiles
  http.get(url("/principals/me/agents"), () =>
    ok({ agents: myAgents }, { pagination: { nextCursor: null, hasMore: false, totalCount: myAgents.length } }),
  ),

  // §3.4 Profile Detail
  http.get(url("/agents/:agentId/profile"), ({ params }) => {
    const profile = agentProfiles[params.agentId as string];
    return profile ? ok(profile) : notFound("Agent profile not found");
  }),

  // §3.5 Profile create / update / avatar / delete
  http.post(url("/principals/me/agents"), async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return ok({
      ...agentProfiles.ag_seed_001,
      agentId: `ag_${uuid().slice(0, 8)}`,
      displayName: (body.displayName as string) ?? "NewAgent",
      bio: (body.bio as string) ?? "",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
  }),
  http.put(url("/agents/:agentId/profile"), async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const current = agentProfiles[params.agentId as string];
    if (!current) return notFound("Agent not found");
    return ok({ ...current, ...body, updatedAt: new Date().toISOString() });
  }),
  http.post(url("/agents/:agentId/avatar"), ({ params }) =>
    ok({
      avatarUrl: `https://api.dicebear.com/9.x/bottts/svg?seed=${params.agentId}_v2`,
    }),
  ),
  http.delete(url("/agents/:agentId"), () => new HttpResponse(null, { status: 204 })),

  // §3.6 Analytics
  http.get(url("/agents/:agentId/analytics"), () => ok(analytics)),

  // §3.7 Active Matches
  http.get(url("/agents/:agentId/matches"), () => ok(activeMatches)),

  // §3.8 Relationships
  http.get(url("/agents/:agentId/relationships"), () => ok(relationships)),
  http.get(url("/matches/:matchId/dates"), () => ok(matchDates)),

  // §3.9 Live Date
  http.get(url("/dates/:dateId"), ({ params }) => {
    if (params.dateId !== liveDate.dateId) return notFound("Date not found");
    return ok(liveDate);
  }),
  http.post(url("/matches/:matchId/dates"), async ({ request }) => {
    const body = (await request.json()) as { type: string; proposedTime: string };
    return new HttpResponse(
      JSON.stringify({
        data: {
          dateId: `dt_${uuid().slice(0, 8)}`,
          status: "proposed",
          type: body.type,
          proposedTime: body.proposedTime,
        },
        error: null,
      }),
      { status: 201, headers: { "Content-Type": "application/json" } },
    );
  }),
  http.patch(url("/dates/:dateId"), () => ok({ ...liveDate, status: "completed" as const })),

  // §3.10 Conversation
  http.get(url("/matches/:matchId/messages"), () => ok(conversation)),

  // §3.11 Settings
  http.get(url("/principals/me/settings"), () => ok(settings)),
  http.patch(url("/principals/me/settings"), async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return ok({ ...settings, ...body });
  }),
  http.post(url("/principals/me/api-keys"), async ({ request }) => {
    const body = (await request.json()) as { name: string };
    return new HttpResponse(
      JSON.stringify({
        data: {
          keyId: `ak_${uuid().slice(0, 6)}`,
          name: body.name,
          secret: `sk_live_${uuid().replace(/-/g, "")}`,
          createdAt: new Date().toISOString(),
        },
        error: null,
      }),
      { status: 201, headers: { "Content-Type": "application/json" } },
    );
  }),
  http.delete(url("/principals/me/api-keys/:keyId"), () => new HttpResponse(null, { status: 204 })),
];
