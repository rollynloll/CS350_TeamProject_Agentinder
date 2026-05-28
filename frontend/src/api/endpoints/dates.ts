import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type {
  DateId,
  EndDateRequest,
  LiveDateResponse,
  MatchId,
  ScheduleDateRequest,
  ScheduleDateResponse,
} from "../types";
import { MIGRATE } from "../migration-flags";
import {
  mapEndRequest,
  mapEndResponse,
  mapLiveDate,
  mapScheduleRequest,
  mapScheduleResponse,
} from "../adapters";
import type { BeDate, BeEndDateResponse } from "../adapters";

export const dateKeys = {
  all: ["dates"] as const,
  live: (dateId: DateId) => ["dates", dateId, "live"] as const,
};

export function useLiveDate(dateId: DateId | undefined) {
  return useQuery({
    queryKey: dateKeys.live(dateId ?? ""),
    queryFn: () =>
      MIGRATE.dateGet
        ? api.get<BeDate>(`/dates/${dateId}`).then(mapLiveDate)
        : api.get<LiveDateResponse>(`/dates/${dateId}`),
    enabled: Boolean(dateId),
  });
}

export function useScheduleDate(matchId: MatchId) {
  return useMutation({
    mutationFn: (body: ScheduleDateRequest) =>
      MIGRATE.dateSchedule
        ? api
            .post<BeDate>(`/matches/${matchId}/dates`, mapScheduleRequest(body))
            .then(mapScheduleResponse)
        : api.post<ScheduleDateResponse, ScheduleDateRequest>(`/matches/${matchId}/dates`, body),
  });
}

export function useEndDate(dateId: DateId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: EndDateRequest) =>
      MIGRATE.dateEnd
        ? api
            .post<BeEndDateResponse>(`/dates/${dateId}/end`, mapEndRequest(body))
            .then(mapEndResponse)
        : api.patch<LiveDateResponse, EndDateRequest>(`/dates/${dateId}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: dateKeys.live(dateId) }),
  });
}
