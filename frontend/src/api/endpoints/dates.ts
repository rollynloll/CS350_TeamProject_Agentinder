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

export const dateKeys = {
  all: ["dates"] as const,
  live: (dateId: DateId) => ["dates", dateId, "live"] as const,
};

export function useLiveDate(dateId: DateId | undefined) {
  return useQuery({
    queryKey: dateKeys.live(dateId ?? ""),
    queryFn: () => api.get<LiveDateResponse>(`/dates/${dateId}`),
    enabled: Boolean(dateId),
  });
}

export function useScheduleDate(matchId: MatchId) {
  return useMutation({
    mutationFn: (body: ScheduleDateRequest) =>
      api.post<ScheduleDateResponse, ScheduleDateRequest>(`/matches/${matchId}/dates`, body),
  });
}

export function useEndDate(dateId: DateId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: EndDateRequest) =>
      api.patch<LiveDateResponse, EndDateRequest>(`/dates/${dateId}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: dateKeys.live(dateId) }),
  });
}
