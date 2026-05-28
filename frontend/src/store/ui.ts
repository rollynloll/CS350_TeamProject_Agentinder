import { create } from "zustand";

export type UiState = {
  sidebarOpen: boolean;
  toast: { id: string; message: string; tone: "info" | "success" | "danger" } | null;
  setSidebar: (open: boolean) => void;
  pushToast: (message: string, tone?: "info" | "success" | "danger") => void;
  dismissToast: () => void;
};

export const useUi = create<UiState>((set) => ({
  sidebarOpen: false,
  toast: null,
  setSidebar: (open) => set({ sidebarOpen: open }),
  pushToast: (message, tone = "info") =>
    set({ toast: { id: crypto.randomUUID?.() ?? String(Date.now()), message, tone } }),
  dismissToast: () => set({ toast: null }),
}));
