import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type {
  AgentCreateRequest,
  AgentId,
  AgentListResponse,
  AgentProfile,
  AgentUpdateRequest,
} from "../types";

export const agentKeys = {
  all: ["agents"] as const,
  myList: () => ["agents", "mine"] as const,
  profile: (agentId: AgentId) => ["agents", agentId, "profile"] as const,
};

export function useMyAgents() {
  return useQuery({
    queryKey: agentKeys.myList(),
    queryFn: () => api.get<AgentListResponse>(`/principals/me/agents`),
  });
}

export function useAgentProfile(agentId: AgentId | undefined) {
  return useQuery({
    queryKey: agentKeys.profile(agentId ?? ""),
    queryFn: () => api.get<AgentProfile>(`/agents/${agentId}/profile`),
    enabled: Boolean(agentId),
  });
}

export function useCreateAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AgentCreateRequest) =>
      api.post<AgentProfile, AgentCreateRequest>(`/principals/me/agents`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: agentKeys.myList() });
    },
  });
}

export function useUpdateAgent(agentId: AgentId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AgentUpdateRequest) =>
      api.put<AgentProfile, AgentUpdateRequest>(`/agents/${agentId}/profile`, body),
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
