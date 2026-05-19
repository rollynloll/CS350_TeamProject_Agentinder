import { useTranslation } from "react-i18next";
import { PageHeader } from "@/design-system/components/PageHeader";
import { Card, CardBody } from "@/design-system/components/Card";

export function AgentCreatePage() {
  const { t } = useTranslation();
  return (
    <>
      <PageHeader title={t("agents.create_title")} />
      <Card>
        <CardBody>
          <p className="text-sm text-text-muted">{t("common.scaffold_notice")}</p>
          <p className="text-sm mt-2">
            Profile wizard will live here: display name, bio, capability tag picker,
            interaction style sliders, availability calendar, avatar upload.
          </p>
        </CardBody>
      </Card>
    </>
  );
}
