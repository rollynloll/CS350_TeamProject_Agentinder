import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Card, CardBody } from "@/design-system/components/Card";
import { useAuth } from "@/store/auth";
import { supabase } from "@/lib/supabase";

/**
 * NOTE: This screen has no Figma mockup yet (neither in the polished
 * Rectangle 61 area nor in the Wireframes frame 30:2234). It only inherits
 * the Phase 0 design tokens. Replace this layout when Login/SignIn designs
 * arrive from Team C.
 */
export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { setSession } = useAuth();

  const devLogin = () => {
    // For real-backend testing, set VITE_DEV_JWT (signed with the backend's
    // SUPABASE_JWT_SECRET) + the seeded principal/agent UUIDs. Falls back to the
    // mock seed identity when unset so pure-mock mode keeps working.
    setSession({
      token: import.meta.env.VITE_DEV_JWT ?? "mock_access_token",
      principalId: import.meta.env.VITE_DEV_PRINCIPAL_ID ?? "pr_seed_dev",
      activeAgentId: import.meta.env.VITE_DEV_AGENT_ID ?? "ag_seed_001",
    });
    navigate("/", { replace: true });
  };

  const loginWithGithub = () => {
    // Supabase가 GitHub OAuth + PKCE + 콜백을 처리한다. 인증 후 /auth/callback 으로 돌아온다.
    void supabase.auth.signInWithOAuth({
      provider: "github",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
  };

  return (
    <Card>
      <CardBody className="p-8 text-center space-y-6">
        <div>
          <h1 className="text-h2 font-bold">Agentinder</h1>
          <p className="text-body1 text-text-muted mt-1">{t("login.description")}</p>
        </div>
        <div className="space-y-2">
          <Button className="w-full" variant="secondary" disabled>
            {t("login.google")}
          </Button>
          <Button className="w-full" variant="secondary" disabled>
            {t("login.microsoft")}
          </Button>
          <Button className="w-full" variant="secondary" onClick={loginWithGithub}>
            {t("login.github")}
          </Button>
        </div>
        <Button className="w-full" onClick={devLogin}>
          {t("login.dev_login")}
        </Button>
      </CardBody>
    </Card>
  );
}
