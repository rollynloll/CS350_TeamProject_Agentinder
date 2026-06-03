import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { SettingsResponse } from "@/api/types";

/**
 * Local settings store — no backend. Persists to localStorage under
 * `agentinder.settings`. Shape mirrors SettingsResponse so consumers that
 * previously read `useSettings().data` can switch to `useSettingsStore()` with
 * minimal change.
 *
 * Backend endpoint (`GET/PATCH /v1/principals/me/settings`) is not implemented;
 * see `docs/missing-backend-apis.md`. Wire `endpoints/settings.ts` back in once
 * it lands.
 */

export type SettingsState = SettingsResponse & {
  updateNotifications: (patch: Partial<SettingsResponse["notifications"]>) => void;
  updatePreferences: (patch: Partial<SettingsResponse["preferences"]>) => void;
  updatePrivacy: (patch: Partial<SettingsResponse["privacy"]>) => void;
  updateAccount: (patch: Partial<SettingsResponse["account"]>) => void;
  addApiKey: (key: SettingsResponse["apiKeys"][number]) => void;
  removeApiKey: (keyId: string) => void;
  reset: () => void;
};

const DEFAULTS: SettingsResponse = {
  account: {
    email: "",
    displayName: "Local User",
    createdAt: new Date(0).toISOString(),
  },
  apiKeys: [],
  notifications: {
    matchAlerts: true,
    dateReminders: true,
    weeklyDigest: true,
    messagePreview: true,
  },
  preferences: {
    globalTrustThreshold: 0.5,
    autoMatchRules: {
      enabled: false,
      minCompatibility: 0.8,
      minTrust: 0.7,
    },
  },
  privacy: {
    profileVisibility: "public",
    dateTranscriptSharing: "mutual_consent",
    analyticsOptIn: true,
  },
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ...DEFAULTS,
      updateNotifications: (patch) =>
        set((s) => ({ notifications: { ...s.notifications, ...patch } })),
      updatePreferences: (patch) =>
        set((s) => ({
          preferences: {
            ...s.preferences,
            ...patch,
            autoMatchRules: {
              ...s.preferences.autoMatchRules,
              ...(patch.autoMatchRules ?? {}),
            },
          },
        })),
      updatePrivacy: (patch) =>
        set((s) => ({ privacy: { ...s.privacy, ...patch } })),
      updateAccount: (patch) =>
        set((s) => ({ account: { ...s.account, ...patch } })),
      addApiKey: (key) =>
        set((s) => ({ apiKeys: [...s.apiKeys, key] })),
      removeApiKey: (keyId) =>
        set((s) => ({ apiKeys: s.apiKeys.filter((k) => k.keyId !== keyId) })),
      reset: () => set({ ...DEFAULTS }),
    }),
    { name: "agentinder.settings" },
  ),
);
