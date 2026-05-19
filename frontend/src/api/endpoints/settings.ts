import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../client";
import type { SettingsPatch, SettingsResponse } from "../types";

export const settingsKeys = {
  all: ["settings"] as const,
  me: () => ["settings", "me"] as const,
};

export function useSettings() {
  return useQuery({
    queryKey: settingsKeys.me(),
    queryFn: () => api.get<SettingsResponse>(`/principals/me/settings`),
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SettingsPatch) =>
      api.patch<SettingsResponse, SettingsPatch>(`/principals/me/settings`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: settingsKeys.me() }),
  });
}

export function useCreateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api.post<{ keyId: string; name: string; secret: string; createdAt: string }, { name: string }>(
        `/principals/me/api-keys`,
        { name },
      ),
    onSuccess: () => qc.invalidateQueries({ queryKey: settingsKeys.me() }),
  });
}

export function useRevokeApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) => api.delete<void>(`/principals/me/api-keys/${keyId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: settingsKeys.me() }),
  });
}
