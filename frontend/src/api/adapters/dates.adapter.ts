import type {
  EndDateRequest,
  LiveDateResponse,
  ScheduleDateRequest,
  ScheduleDateResponse,
} from "../types";
import type { BeDate, BeEndDateRequest, BeEndDateResponse } from "./backend-types";
import { avatarOrFallback, normalizeDateType, nowIso, partnerLabel } from "./defaults";

function liveStatus(be: BeDate): LiveDateResponse["status"] {
  if (be.is_noshow) return "no_show";
  if (be.ended_at) return "completed";
  if (be.started_at) return "in_progress";
  return "proposed";
}

function elapsed(be: BeDate): number {
  if (!be.started_at) return 0;
  const end = be.ended_at ? new Date(be.ended_at).getTime() : Date.now();
  return Math.max(0, Math.round((end - new Date(be.started_at).getTime()) / 60000));
}

export function mapLiveDate(be: BeDate): LiveDateResponse {
  return {
    dateId: be.date_id,
    type: normalizeDateType(be.type),
    status: liveStatus(be),
    partnerAgent: {
      agentId: "",
      displayName: partnerLabel(be.match_id),
      avatarUrl: avatarOrFallback(null, be.match_id),
      trustScore: null,
    },
    startedAt: be.started_at ?? be.created_at,
    maxDurationMinutes: 15,
    elapsedMinutes: elapsed(be),
    icebreakers: [],
    recentMessages: [],
  };
}

export function mapScheduleRequest(req: ScheduleDateRequest): { type: string; scheduled_at: string } {
  return { type: req.type, scheduled_at: req.proposedTime };
}

export function mapScheduleResponse(be: BeDate): ScheduleDateResponse {
  return {
    dateId: be.date_id,
    status: liveStatus(be),
    type: normalizeDateType(be.type),
    proposedTime: be.scheduled_at ?? be.created_at,
  };
}

// NOTE: rated_agent_id is not available from the frontend EndDateRequest, so the
// rating is not submitted to the backend (the date still ends). Threading the
// partner agent id through the UI is a follow-up.
export function mapEndRequest(req: EndDateRequest): BeEndDateRequest {
  const compat = req.compatibility ?? req.rating;
  return {
    outcome: req.outcome,
    rating_stars: req.rating,
    rating_compatibility: compat != null ? compat / 5 : undefined,
  };
}

export function mapEndResponse(be: BeEndDateResponse): LiveDateResponse {
  return {
    dateId: be.date_id,
    type: "coffee_chat",
    status: "completed",
    partnerAgent: { agentId: "", displayName: "", avatarUrl: "", trustScore: null },
    startedAt: nowIso(),
    maxDurationMinutes: 15,
    elapsedMinutes: 0,
    icebreakers: [],
    recentMessages: [],
  };
}
