import { useEffect } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Home, MessageCircle, Search, Settings as SettingsIcon, UserSquare2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/store/auth";
import { useSettingsStore } from "@/store/settings";
import { ensurePrincipal } from "@/api/endpoints/principals";
import { useMyAgents } from "@/api/endpoints/agents";
import { wsClient } from "@/api/ws/client";
import { useWsStatus } from "@/api/ws/hooks";
import { cn } from "@/lib/cn";
import { topics } from "@/api/ws/topics";
import { MobileShell } from "./MobileShell";
import { BottomNav } from "@/design-system/components/BottomNav";

// Figma primary nav: home / search / chat / profile, with settings via gear.
// Relationships + Analytics live inside the Profile tab (not top-level nav).
const sidebarItems = [
  { to: "/", icon: Home, key: "home" },
  { to: "/discover", icon: Search, key: "search" },
  { to: "/matches", icon: MessageCircle, key: "chat" },
  { to: "/agents", icon: UserSquare2, key: "profile" },
  { to: "/settings", icon: SettingsIcon, key: "settings" },
] as const;

export function AuthedLayout() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { token, activeAgentId } = useAuth();
  const wsStatus = useWsStatus();

  // 로그인 후 에이전트 목록을 가져와 activeAgentId 를 자동 선택한다.
  // React Query 캐시를 공유하므로 MyAgentsPage 등 다른 곳에서도 중복 요청 없이 재사용된다.
  const { data: agentsData, isSuccess: agentsLoaded } = useMyAgents();
  useEffect(() => {
    if (!agentsLoaded) return;
    const agents = agentsData?.agents ?? [];
    if (agents.length === 0) return;
    const { activeAgentId: cur, setActiveAgent } = useAuth.getState();
    // 현재 선택된 에이전트가 없거나 목록에서 사라진 경우 첫 번째 에이전트로 설정한다.
    if (!cur || !agents.some((a) => a.agentId === cur)) {
      setActiveAgent(agents[0].agentId);
    }
  }, [agentsLoaded, agentsData]);

  useEffect(() => {
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    let cancelled = false;
    // 로그인 직후 회원 레코드를 보장(멱등)한 뒤 WS를 연결한다.
    // principal이 없는 상태로 WS가 붙어 인증 실패하는 것을 막는다.
    void (async () => {
      try {
        const p = await ensurePrincipal();
        if (!cancelled && p?.principal_id) {
          // 백엔드(JWT sub) 기준 principal_id를 권위값으로 store에 반영.
          // setSession/activeAgentId는 getState로 읽어 effect deps를 늘리지 않는다.
          const { setSession, activeAgentId } = useAuth.getState();
          setSession({
            token,
            principalId: p.principal_id,
            activeAgentId: activeAgentId ?? undefined,
          });
          // 유저 정보(이메일, 이름)를 settings store에 반영한다.
          useSettingsStore.getState().updateAccount({
            email: p.email ?? "",
            displayName: p.name ?? "",
            createdAt: p.created_at ?? new Date(0).toISOString(),
          });
        }
      } catch (err) {
        // 토큰 만료 등은 후속 API 호출에서 401로 처리된다.
        console.error("ensurePrincipal failed", err);
      } finally {
        if (!cancelled) wsClient.connect();
      }
    })();
    return () => {
      cancelled = true;
      wsClient.disconnect();
    };
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
      <aside className="hidden md:flex w-60 flex-col border-r border-border bg-bg">
        <div className="px-5 py-5">
          <div className="text-h2 font-bold tracking-tight text-text">{t("app.name")}</div>
          <div className="text-body2 text-text-muted">{t("app.tagline")}</div>
        </div>
        <nav className="flex-1 px-3 py-2 space-y-2">
          {sidebarItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-body1 transition-all",
                  isActive
                    ? "bg-surface shadow-inset text-primary font-semibold"
                    : "text-text-muted hover:text-text hover:bg-surface hover:shadow-float",
                )
              }
            >
              <item.icon className="w-[18px] h-[18px]" />
              <span>{t(`nav.${item.key}` as const, { defaultValue: item.key })}</span>
            </NavLink>
          ))}
        </nav>
        <div className="mx-3 mb-4 px-4 py-3 rounded-xl bg-surface shadow-float text-body2 text-text-muted flex items-center justify-between">
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
