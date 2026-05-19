import { useTranslation } from "react-i18next";
import { useSettings } from "@/api/endpoints/settings";
import { Badge } from "@/design-system/components/Badge";
import { Button } from "@/design-system/components/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/design-system/components/Card";
import { PageHeader } from "@/design-system/components/PageHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { useAuth } from "@/store/auth";

export function SettingsPage() {
  const { t } = useTranslation();
  const query = useSettings();
  const { logout } = useAuth();

  return (
    <>
      <PageHeader title={t("settings.title")} description={t("settings.description")} />
      <QueryBoundary query={query}>
        {(s) => (
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Account</CardTitle>
              </CardHeader>
              <CardBody className="space-y-1 text-sm">
                <div>{s.account.displayName}</div>
                <div className="text-text-muted">{s.account.email}</div>
                <Button variant="ghost" size="sm" className="mt-2" onClick={() => logout()}>
                  Log out
                </Button>
              </CardBody>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Notifications</CardTitle>
              </CardHeader>
              <CardBody className="space-y-1 text-sm">
                {Object.entries(s.notifications).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between">
                    <span>{k}</span>
                    <Badge tone={v ? "trust" : "neutral"}>{v ? "on" : "off"}</Badge>
                  </div>
                ))}
              </CardBody>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Trust threshold</CardTitle>
              </CardHeader>
              <CardBody className="text-sm">
                Global minimum: {s.preferences.globalTrustThreshold.toFixed(2)}
                <p className="text-xs text-text-muted mt-1">
                  Auto-match{" "}
                  {s.preferences.autoMatchRules.enabled ? "enabled" : "disabled"}
                </p>
              </CardBody>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>API keys</CardTitle>
              </CardHeader>
              <CardBody className="space-y-2 text-sm">
                {s.apiKeys.map((k) => (
                  <div key={k.keyId} className="flex items-center justify-between">
                    <span>{k.name}</span>
                    <Button variant="ghost" size="sm">
                      Revoke
                    </Button>
                  </div>
                ))}
              </CardBody>
            </Card>
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle>Danger zone</CardTitle>
              </CardHeader>
              <CardBody className="flex flex-wrap gap-2">
                <Button variant="secondary" size="sm">
                  Pause all agents
                </Button>
                <Button variant="danger" size="sm">
                  Activate kill switch
                </Button>
              </CardBody>
            </Card>
          </div>
        )}
      </QueryBoundary>
    </>
  );
}
