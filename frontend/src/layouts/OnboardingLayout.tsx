import { useEffect } from "react";
import { Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/store/auth";
import { isOnboarded } from "@/lib/onboarding";
import { ensurePrincipal } from "@/api/endpoints/principals";
import { MobileShell } from "./MobileShell";

/**
 * Fullscreen onboarding chrome: no sidebar, no BottomNav. Token-gated like the
 * app, but bounces already-onboarded users back to the app so /onboarding can't
 * be revisited by typing the URL.
 */
export function OnboardingLayout() {
  const navigate = useNavigate();
  const { token } = useAuth();

  useEffect(() => {
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    if (isOnboarded()) {
      navigate("/", { replace: true });
      return;
    }
    // Ensure the principal exists before the agent-creation step (POST /v1/agents
    // requires it). Mirrors AuthedLayout's idempotent ensure.
    let cancelled = false;
    void (async () => {
      try {
        const p = await ensurePrincipal();
        if (!cancelled && p?.principal_id) {
          const { setSession, activeAgentId } = useAuth.getState();
          setSession({ token, principalId: p.principal_id, activeAgentId: activeAgentId ?? undefined });
        }
      } catch (err) {
        console.error("ensurePrincipal failed", err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, navigate]);

  if (!token) return null;

  return (
    <div className="h-full flex overflow-hidden">
      <MobileShell>
        <main className="flex-1 min-h-0 flex flex-col overflow-hidden">
          <Outlet />
        </main>
      </MobileShell>
    </div>
  );
}
