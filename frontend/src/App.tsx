import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { useEffect } from "react";
import "./i18n";
import { router } from "./router";
import { setAuthTokenGetter } from "./api/client";
import { useAuth } from "./store/auth";
import { wsClient } from "./api/ws/client";
import { MockWebSocket } from "./mocks/ws-broker";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const USE_MOCK =
  import.meta.env.VITE_USE_MOCK === "true" || import.meta.env.VITE_USE_MOCK === undefined;

export function App() {
  useEffect(() => {
    setAuthTokenGetter(() => useAuth.getState().token);
    wsClient.configure({
      tokenGetter: () => useAuth.getState().token,
      // When using MSW, swap real WebSocket for the in-memory mock
      wsCtor: USE_MOCK
        ? (MockWebSocket as unknown as new (url: string) => WebSocket)
        : (WebSocket as unknown as new (url: string) => WebSocket),
    });
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
