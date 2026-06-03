import { MobileHeader } from "@/design-system/components/MobileHeader";
import { useSettingsStore } from "@/store/settings";
import type { SettingsResponse } from "@/api/types";
import { ToggleRow } from "./components/ToggleRow";
import { cn } from "@/lib/cn";

const visibilityOptions: Array<SettingsResponse["privacy"]["profileVisibility"]> = [
  "public",
  "restricted",
  "hidden",
];

const transcriptOptions: Array<
  SettingsResponse["privacy"]["dateTranscriptSharing"]
> = ["mutual_consent", "owner_only", "platform"];

export function PrivacyPage() {
  const privacy = useSettingsStore((s) => s.privacy);
  const updatePrivacy = useSettingsStore((s) => s.updatePrivacy);

  return (
    <>
      <MobileHeader showBack title="Privacy control" />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-3">
        <section className="rounded-2xl bg-surface shadow-card p-4 space-y-3">
          <div className="text-body2 font-semibold text-text-muted">
            Profile visibility
          </div>
          <div className="flex gap-2">
            {visibilityOptions.map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => updatePrivacy({ profileVisibility: opt })}
                className={cn(
                  "flex-1 rounded-full px-3 py-2 text-body2 font-semibold border capitalize transition-colors",
                  privacy.profileVisibility === opt
                    ? "bg-primary text-primary-fg border-primary"
                    : "bg-surface text-text-muted border-border",
                )}
              >
                {opt}
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-2xl bg-surface shadow-card p-4 space-y-3">
          <div className="text-body2 font-semibold text-text-muted">
            Date transcript sharing
          </div>
          <div className="flex flex-col gap-2">
            {transcriptOptions.map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => updatePrivacy({ dateTranscriptSharing: opt })}
                className={cn(
                  "rounded-xl px-3 py-2 text-body1 font-medium border text-left transition-colors",
                  privacy.dateTranscriptSharing === opt
                    ? "bg-danger-light text-primary border-primary"
                    : "bg-surface text-text-muted border-border",
                )}
              >
                {opt.replace(/_/g, " ")}
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-2xl bg-surface shadow-card divide-y divide-border">
          <ToggleRow
            label="Share usage analytics"
            description="Help us improve. No conversation content is shared."
            enabled={privacy.analyticsOptIn}
            onToggle={(next) => updatePrivacy({ analyticsOptIn: next })}
          />
        </section>
      </div>
    </>
  );
}
