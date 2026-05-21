import { useEffect } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Compass,
  Heart,
  MessageCircle,
  Network,
  Settings as SettingsIcon,
  Sparkles,
  UserSquare2,
  BarChart3,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/store/auth";
import { wsClient } from "@/api/ws/client";
import { useWsStatus } from "@/api/ws/hooks";
import { cn } from "@/lib/cn";
import { topics } from "@/api/ws/topics";
import { MobileShell } from "./MobileShell";
import { BottomNav } from "@/design-system/components/BottomNav";

const sidebarItems = [
  { to: "/", icon: Sparkles, key: "feed" },
  { to: "/discover", icon: Compass, key: "discover" },
  { to: "/agents", icon: UserSquare2, key: "agents" },
  { to: "/matches", icon: Heart, key: "matches" },
  { to: "/conversations/mt_seed_001", icon: MessageCircle, key: "conversation" },
  { to: "/relationships", icon: Network, key: "relationships" },
  { to: "/analytics", icon: BarChart3, key: "analytics" },
  { to: "/settings", icon: SettingsIcon, key: "settings" },
] as const;

export function AuthedLayout() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { token, activeAgentId } = useAuth();
  const wsStatus = useWsStatus();

  useEffect(() => {
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    wsClient.connect();
    return () => wsClient.disconnect();
  }, [token, navigate]);

  useEffect(() => {
    if (!activeAgentId) return;
    return wsClient.subscribe(topics.matches(activeAgentId), () => {
      // Layout-level subscribe keeps the WS warm; feature pages own real handlers.
    });
  }, [activeAgentId]);

  if (!token) return null;

  return (
    <div className="h-full flex overflow-hidden">
      <aside className="hidden md:flex w-60 flex-col border-r border-border bg-surface">
        <div className="px-5 py-4 border-b border-border">
          <div className="text-lg font-bold tracking-tight">{t("app.name")}</div>
          <div className="text-xs text-text-muted">{t("app.tagline")}</div>
        </div>
        <nav className="flex-1 py-3 space-y-1">
          {sidebarItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 mx-2 px-3 py-2 rounded-md text-sm",
                  isActive
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-text hover:bg-surface-2",
                )
              }
            >
              <item.icon className="w-4 h-4" />
              <span>{t(`nav.${item.key}` as const, { defaultValue: item.key })}</span>
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-3 border-t border-border text-xs text-text-muted flex items-center justify-between">
          <span>WS</span>
          <span
            className={cn(
              "inline-flex items-center gap-1",
              wsStatus === "open"
                ? "text-trust"
                : wsStatus === "reconnecting"
                  ? "text-warning"
                  : "text-text-muted",
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                wsStatus === "open"
                  ? "bg-trust"
                  : wsStatus === "reconnecting"
                    ? "bg-warning"
                    : "bg-text-muted",
              )}
            />
            {wsStatus}
          </span>
        </div>
      </aside>

      <MobileShell>
        <main className="flex-1 min-h-0 flex flex-col overflow-hidden">
          <Outlet />
        </main>
        <BottomNav />
      </MobileShell>
    </div>
  );
}
