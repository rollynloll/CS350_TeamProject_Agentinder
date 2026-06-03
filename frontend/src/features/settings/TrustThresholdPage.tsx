import * as Slider from "@radix-ui/react-slider";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { useSettingsStore } from "@/store/settings";

export function TrustThresholdPage() {
  const value = useSettingsStore((s) => s.preferences.globalTrustThreshold);
  const updatePreferences = useSettingsStore((s) => s.updatePreferences);
  const setValue = (v: number) => updatePreferences({ globalTrustThreshold: v });

  return (
    <>
      <MobileHeader showBack title="Global trust threshold" />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-3">
        <section className="rounded-2xl bg-surface shadow-card p-4 space-y-4">
          <p className="text-body1 text-text-muted">
            Only show matches whose trust score meets or exceeds this minimum.
          </p>
          <div className="flex items-baseline justify-between">
            <span className="text-body2 font-semibold text-text-muted">
              Minimum trust
            </span>
            <span className="text-h2 font-bold text-primary tabular-nums">
              {value.toFixed(2)}
            </span>
          </div>
          <Slider.Root
            value={[value]}
            onValueChange={([v]) => setValue(v)}
            min={0}
            max={1}
            step={0.05}
            className="relative flex items-center select-none touch-none w-full h-5"
          >
            <Slider.Track className="bg-surface-2 relative grow rounded-full h-1.5">
              <Slider.Range className="absolute bg-primary rounded-full h-full" />
            </Slider.Track>
            <Slider.Thumb
              aria-label="Minimum trust"
              className="block w-4 h-4 bg-primary rounded-full shadow-card focus:outline-none focus:ring-2 focus:ring-primary/40"
            />
          </Slider.Root>
        </section>
      </div>
    </>
  );
}
