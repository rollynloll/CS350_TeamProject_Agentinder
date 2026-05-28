import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@/design-system/components/Button";
import { Card, CardBody } from "@/design-system/components/Card";
import { useAuth } from "@/store/auth";

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
    setSession({
      token: "mock_access_token",
      principalId: "pr_seed_dev",
      activeAgentId: "ag_seed_001",
    });
    navigate("/", { replace: true });
  };

  return (
    <Card>
      <CardBody className="p-8 text-center space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Agentinder</h1>
          <p className="text-sm text-text-muted mt-1">{t("login.description")}</p>
        </div>
        <div className="space-y-2">
          <Button className="w-full" variant="secondary" disabled>
            {t("login.google")}
          </Button>
          <Button className="w-full" variant="secondary" disabled>
            {t("login.microsoft")}
          </Button>
          <Button className="w-full" variant="secondary" disabled>
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
