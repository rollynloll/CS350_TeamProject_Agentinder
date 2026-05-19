import { createBrowserRouter, Navigate } from "react-router-dom";
import { AuthedLayout } from "./layouts/AuthedLayout";
import { PublicLayout } from "./layouts/PublicLayout";
import { LoginPage } from "./features/login/LoginPage";
import { FeedPage } from "./features/feed/FeedPage";
import { DiscoverPage } from "./features/discover/DiscoverPage";
import { MyAgentsPage } from "./features/agents/MyAgentsPage";
import { AgentCreatePage } from "./features/agents/AgentCreatePage";
import { AgentDetailPage } from "./features/agents/AgentDetailPage";
import { AgentEditPage } from "./features/agents/AgentEditPage";
import { AnalyticsPage } from "./features/analytics/AnalyticsPage";
import { MatchesPage } from "./features/matches/MatchesPage";
import { ConversationPage } from "./features/conversation/ConversationPage";
import { DateHistoryPage } from "./features/date-history/DateHistoryPage";
import { DateLivePage } from "./features/date-live/DateLivePage";
import { RelationshipsPage } from "./features/relationships/RelationshipsPage";
import { SettingsPage } from "./features/settings/SettingsPage";

export const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [{ path: "/login", element: <LoginPage /> }],
  },
  {
    element: <AuthedLayout />,
    children: [
      { path: "/", element: <FeedPage /> },
      { path: "/discover", element: <DiscoverPage /> },
      { path: "/agents", element: <MyAgentsPage /> },
      { path: "/agents/new", element: <AgentCreatePage /> },
      { path: "/agents/:agentId", element: <AgentDetailPage /> },
      { path: "/agents/:agentId/edit", element: <AgentEditPage /> },
      { path: "/analytics", element: <AnalyticsPage /> },
      { path: "/matches", element: <MatchesPage /> },
      { path: "/conversations/:matchId", element: <ConversationPage /> },
      { path: "/matches/:matchId/history", element: <DateHistoryPage /> },
      { path: "/dates/:dateId", element: <DateLivePage /> },
      { path: "/relationships", element: <RelationshipsPage /> },
      { path: "/settings", element: <SettingsPage /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
