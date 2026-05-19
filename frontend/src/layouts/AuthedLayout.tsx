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

const navItems = [
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

  // Connect WS once on mount; subscribe to per-agent matches topic.
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
      // Real handler lives in features/matches; this layout-level subscribe just
      // ensures the connection has at least one topic during the scaffold phase.
    });
  }, [activeAgentId]);

  if (!token) return null;

  return (
    <div className="min-h-full flex">
      <aside className="hidden md:flex w-60 flex-col border-r border-border bg-surface">
        <div className="px-5 py-4 border-b border-border">
          <div className="text-lg font-bold tracking-tight">{t("app.name")}</div>
          <div className="text-xs text-text-muted">{t("app.tagline")}</div>
        </div>
        <nav className="flex-1 py-3 space-y-1">
          {navItems.map((item) => (
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
                ? "text-success"
                : wsStatus === "reconnecting"
                  ? "text-warning"
                  : "text-text-muted",
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                wsStatus === "open"
                  ? "bg-success"
                  : wsStatus === "reconnecting"
                    ? "bg-warning"
                    : "bg-text-muted",
              )}
            />
            {wsStatus}
          </span>
        </div>
      </aside>

      <main className="flex-1 overflow-auto">
        <div className="max-w-5xl mx-auto px-4 md:px-8 py-6">
          <Outlet />
        </div>
      </main>

      <nav className="md:hidden fixed bottom-0 inset-x-0 border-t border-border bg-surface flex justify-around py-2">
        {navItems.slice(0, 5).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "flex flex-col items-center text-[10px] px-2 py-1 rounded-md",
                isActive ? "text-primary" : "text-text-muted",
              )
            }
          >
            <item.icon className="w-5 h-5 mb-0.5" />
            {t(`nav.${item.key}` as const, { defaultValue: item.key })}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
