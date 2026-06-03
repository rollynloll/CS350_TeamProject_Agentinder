import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type {
  AgentCreateRequest,
  AgentId,
  AgentListResponse,
  AgentProfile,
  AgentUpdateRequest,
} from "../types";
import { MIGRATE } from "../migration-flags";
import {
  mapAgentList,
  mapAgentProfile,
  mapCreateRequest,
  mapCreateResponse,
  mapUpdateRequest,
  mapUpdateResponse,
} from "../adapters";
import type {
  BeAgentListItem,
  BeAgentProfile,
  BeCreateAgentResponse,
  BeUpdateAgentResponse,
} from "../adapters";

export const agentKeys = {
  all: ["agents"] as const,
  myList: () => ["agents", "mine"] as const,
  profile: (agentId: AgentId) => ["agents", agentId, "profile"] as const,
};

export function useMyAgents() {
  return useQuery({
    queryKey: agentKeys.myList(),
    queryFn: () =>
      MIGRATE.agentsList
        ? api.get<BeAgentListItem[]>(`/agents`).then(mapAgentList)
        : api.get<AgentListResponse>(`/principals/me/agents`),
  });
}

export function useAgentProfile(agentId: AgentId | undefined) {
  return useQuery({
    queryKey: agentKeys.profile(agentId ?? ""),
    queryFn: () =>
      MIGRATE.agentProfile
        ? api.get<BeAgentProfile>(`/agents/${agentId}`).then((be) => mapAgentProfile(be))
        : api.get<AgentProfile>(`/agents/${agentId}/profile`),
    enabled: Boolean(agentId),
  });
}

export function useCreateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AgentCreateRequest) =>
      MIGRATE.agentCreate
        ? api
            .post<BeCreateAgentResponse>(`/agents`, mapCreateRequest(body))
            .then((be) => mapCreateResponse(be, body))
        : api.post<AgentProfile, AgentCreateRequest>(`/principals/me/agents`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: agentKeys.myList() });
    },
  });
}

export function useUpdateAgent(agentId: AgentId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AgentUpdateRequest) =>
      MIGRATE.agentUpdate
        ? api
            .patch<BeUpdateAgentResponse>(`/agents/${agentId}`, mapUpdateRequest(body))
            .then((be) =>
              mapUpdateResponse(be, qc.getQueryData<AgentProfile>(agentKeys.profile(agentId))),
            )
        : api.put<AgentProfile, AgentUpdateRequest>(`/agents/${agentId}/profile`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: agentKeys.profile(agentId) });
      qc.invalidateQueries({ queryKey: agentKeys.myList() });
    },
  });
}

export function useUploadAvatar(agentId: AgentId) {
  return useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.post<{ avatarUrl: string }>(`/agents/${agentId}/avatar`, fd);
    },
  });
}

export function useDeleteAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (agentId: AgentId) => api.delete<void>(`/agents/${agentId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: agentKeys.myList() }),
  });
}
