import { MobileHeader } from "@/design-system/components/MobileHeader";
import { useSettingsStore } from "@/store/settings";
import type { SettingsResponse } from "@/api/types";
import { ToggleRow } from "./components/ToggleRow";

const labels: Record<keyof SettingsResponse["notifications"], string> = {
  matchAlerts: "Match alerts",
  dateReminders: "Date reminders",
  weeklyDigest: "Weekly digest",
  messagePreview: "Message preview",
};

export function NoticePage() {
  const notifications = useSettingsStore((s) => s.notifications);
  const updateNotifications = useSettingsStore((s) => s.updateNotifications);

  return (
    <>
      <MobileHeader showBack title="Notice" />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6">
        <section className="rounded-2xl bg-surface shadow-card divide-y divide-border">
          {(Object.keys(labels) as Array<keyof typeof labels>).map((key) => (
            <ToggleRow
              key={key}
              label={labels[key]}
              enabled={notifications[key]}
              onToggle={(next) => updateNotifications({ [key]: next })}
            />
          ))}
        </section>
      </div>
    </>
  );
}
