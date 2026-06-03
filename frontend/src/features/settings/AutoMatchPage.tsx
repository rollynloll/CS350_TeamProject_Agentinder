import * as Slider from "@radix-ui/react-slider";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { useSettingsStore } from "@/store/settings";
import { ToggleRow } from "./components/ToggleRow";

export function AutoMatchPage() {
  const autoMatchRules = useSettingsStore((s) => s.preferences.autoMatchRules);
  const updatePreferences = useSettingsStore((s) => s.updatePreferences);

  const patch = (k: keyof typeof autoMatchRules, v: boolean | number) =>
    updatePreferences({ autoMatchRules: { ...autoMatchRules, [k]: v } });

  return (
    <>
      <MobileHeader showBack title="Auto-match rule" />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-3">
        <section className="rounded-2xl bg-surface shadow-card divide-y divide-border">
          <ToggleRow
            label="Auto-match enabled"
            description="Automatically accept candidates that meet thresholds below."
            enabled={autoMatchRules.enabled}
            onToggle={(next) => patch("enabled", next)}
          />
        </section>
        <ThresholdCard
          label="Minimum compatibility"
          value={autoMatchRules.minCompatibility}
          onChange={(v) => patch("minCompatibility", v)}
        />
        <ThresholdCard
          label="Minimum trust"
          value={autoMatchRules.minTrust}
          onChange={(v) => patch("minTrust", v)}
        />
      </div>
    </>
  );
}

function ThresholdCard({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <section className="rounded-2xl bg-surface shadow-card p-4 space-y-3">
      <div className="flex items-baseline justify-between">
        <span className="text-body2 font-semibold text-text-muted">{label}</span>
        <span className="text-h2 font-bold text-primary tabular-nums">
          {value.toFixed(2)}
        </span>
      </div>
      <Slider.Root
        value={[value]}
        onValueChange={([v]) => onChange(v)}
        min={0}
        max={1}
        step={0.05}
        className="relative flex items-center select-none touch-none w-full h-5"
      >
        <Slider.Track className="bg-surface-2 relative grow rounded-full h-1.5">
          <Slider.Range className="absolute bg-primary rounded-full h-full" />
        </Slider.Track>
        <Slider.Thumb
          aria-label={label}
          className="block w-4 h-4 bg-primary rounded-full shadow-card focus:outline-none focus:ring-2 focus:ring-primary/40"
        />
      </Slider.Root>
    </section>
  );
}
