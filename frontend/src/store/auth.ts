import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AgentId } from "@/api/types";

export type AuthState = {
  token: string | null;
  principalId: string | null;
  // Currently-selected agent (most views are per-agent).
  activeAgentId: AgentId | null;

  setSession: (s: { token: string; principalId: string; activeAgentId?: AgentId }) => void;
  setActiveAgent: (agentId: AgentId | null) => void;
  logout: () => void;
};

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      principalId: null,
      activeAgentId: null,
      setSession: ({ token, principalId, activeAgentId }) =>
        set({ token, principalId, activeAgentId: activeAgentId ?? null }),
      setActiveAgent: (agentId) => set({ activeAgentId: agentId }),
      logout: () => set({ token: null, principalId: null, activeAgentId: null }),
    }),
    { name: "agentinder.auth" },
  ),
);
