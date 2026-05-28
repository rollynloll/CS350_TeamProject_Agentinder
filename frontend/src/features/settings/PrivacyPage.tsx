import { useState } from "react";
import { useSettings } from "@/api/endpoints/settings";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
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
  const query = useSettings();

  return (
    <>
      <MobileHeader showBack title="Privacy control" />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-3">
        <QueryBoundary query={query}>
          {(s) => <PrivacyForm initial={s.privacy} />}
        </QueryBoundary>
      </div>
    </>
  );
}

function PrivacyForm({ initial }: { initial: SettingsResponse["privacy"] }) {
  const [values, setValues] = useState(initial);
  return (
    <>
      <section className="rounded-2xl bg-surface shadow-card p-4 space-y-3">
        <div className="text-xs font-semibold text-text-muted">
          Profile visibility
        </div>
        <div className="flex gap-2">
          {visibilityOptions.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() =>
                setValues((prev) => ({ ...prev, profileVisibility: opt }))
              }
              className={cn(
                "flex-1 rounded-full px-3 py-2 text-xs font-semibold border capitalize transition-colors",
                values.profileVisibility === opt
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
        <div className="text-xs font-semibold text-text-muted">
          Date transcript sharing
        </div>
        <div className="flex flex-col gap-2">
          {transcriptOptions.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() =>
                setValues((prev) => ({ ...prev, dateTranscriptSharing: opt }))
              }
              className={cn(
                "rounded-xl px-3 py-2 text-sm font-medium border text-left transition-colors",
                values.dateTranscriptSharing === opt
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
          enabled={values.analyticsOptIn}
          onToggle={(next) =>
            setValues((prev) => ({ ...prev, analyticsOptIn: next }))
          }
        />
      </section>
    </>
  );
}
