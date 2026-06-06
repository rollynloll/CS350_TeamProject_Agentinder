import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { useEffect } from "react";
import "./i18n";
import { router } from "./router";
import { setAuthTokenGetter } from "./api/client";
import { useAuth } from "./store/auth";
import { wsClient } from "./api/ws/client";
import { MockWebSocket } from "./mocks/ws-broker";
import { supabase } from "./lib/supabase";

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

    // Supabase autoRefreshToken이 토큰을 갱신할 때 auth store와 WS 연결을 갱신한다.
    // 갱신 없이는 1시간 후 WS 인증이 만료되어 403 반복 오류가 발생한다.
    const { data: sub } = supabase.auth.onAuthStateChange((event, session) => {
      if ((event === "TOKEN_REFRESHED" || event === "SIGNED_IN") && session) {
        const { setSession, activeAgentId } = useAuth.getState();
        setSession({
          token: session.access_token,
          principalId: session.user.id,
          email: session.user.email,
          activeAgentId: activeAgentId ?? undefined,
        });
        // WS가 연결 중이면 새 토큰으로 재연결한다.
        wsClient.disconnect();
        wsClient.connect();
      }
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
