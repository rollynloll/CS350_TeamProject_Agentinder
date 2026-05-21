import { useState } from "react";
import { useSettings } from "@/api/endpoints/settings";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import type { SettingsResponse } from "@/api/types";
import { ToggleRow } from "./components/ToggleRow";

const labels: Record<keyof SettingsResponse["notifications"], string> = {
  matchAlerts: "Match alerts",
  dateReminders: "Date reminders",
  weeklyDigest: "Weekly digest",
  messagePreview: "Message preview",
};

export function NoticePage() {
  const query = useSettings();

  return (
    <>
      <MobileHeader showBack title="Notice" />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6">
        <QueryBoundary query={query}>
          {(s) => <NoticeForm initial={s.notifications} />}
        </QueryBoundary>
      </div>
    </>
  );
}

function NoticeForm({
  initial,
}: {
  initial: SettingsResponse["notifications"];
}) {
  const [values, setValues] = useState(initial);
  return (
    <section className="rounded-2xl bg-surface shadow-card divide-y divide-border">
      {(Object.keys(labels) as Array<keyof typeof labels>).map((key) => (
        <ToggleRow
          key={key}
          label={labels[key]}
          enabled={values[key]}
          onToggle={(next) => setValues((prev) => ({ ...prev, [key]: next }))}
        />
      ))}
    </section>
  );
}
