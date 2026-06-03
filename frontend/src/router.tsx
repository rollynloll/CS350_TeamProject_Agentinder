import { createBrowserRouter, Navigate } from "react-router-dom";
import { AuthedLayout } from "./layouts/AuthedLayout";
import { PublicLayout } from "./layouts/PublicLayout";
import { LoginPage } from "./features/login/LoginPage";
import { AuthCallbackPage } from "./features/login/AuthCallbackPage";
import { FeedPage } from "./features/feed/FeedPage";
import { DiscoverPage } from "./features/discover/DiscoverPage";
import { MyAgentsPage } from "./features/agents/MyAgentsPage";
import { AgentCreatePage } from "./features/agents/AgentCreatePage";
import { AgentDetailPage } from "./features/agents/AgentDetailPage";
import { AgentEditPage } from "./features/agents/AgentEditPage";
import { AnalyticsPage } from "./features/analytics/AnalyticsPage";
import { MatchesPage } from "./features/matches/MatchesPage";
import { StartDatePage } from "./features/matches/StartDatePage";
import { DateResultPage } from "./features/matches/DateResultPage";
import { ConversationPage } from "./features/conversation/ConversationPage";
import { DateHistoryPage } from "./features/date-history/DateHistoryPage";
import { DateLivePage } from "./features/date-live/DateLivePage";
import { RelationshipsPage } from "./features/relationships/RelationshipsPage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { AccountPage } from "./features/settings/AccountPage";
import { ApiKeysPage } from "./features/settings/ApiKeysPage";
import { NoticePage } from "./features/settings/NoticePage";
import { PrivacyPage } from "./features/settings/PrivacyPage";
import { TrustThresholdPage } from "./features/settings/TrustThresholdPage";
import { AutoMatchPage } from "./features/settings/AutoMatchPage";

export const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    children: [
      { path: "/login", element: <LoginPage /> },
      { path: "/auth/callback", element: <AuthCallbackPage /> },
    ],
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
      { path: "/matches/:matchId/start", element: <StartDatePage /> },
      { path: "/matches/:matchId/result", element: <DateResultPage /> },
      { path: "/conversations/:matchId", element: <ConversationPage /> },
      { path: "/matches/:matchId/history", element: <DateHistoryPage /> },
      { path: "/dates/:dateId", element: <DateLivePage /> },
      { path: "/relationships", element: <RelationshipsPage /> },
      { path: "/settings", element: <SettingsPage /> },
      { path: "/settings/account", element: <AccountPage /> },
      { path: "/settings/api-keys", element: <ApiKeysPage /> },
      { path: "/settings/notice", element: <NoticePage /> },
      { path: "/settings/privacy", element: <PrivacyPage /> },
      { path: "/settings/trust-threshold", element: <TrustThresholdPage /> },
      { path: "/settings/auto-match", element: <AutoMatchPage /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
