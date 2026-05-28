import { cn } from "@/lib/cn";

/**
 * Settings-style toggle row: label on the left, pill-shaped on/off switch on
 * the right. Visual + controlled; the parent owns the boolean state and the
 * eventual mutation wiring.
 */
export function ToggleRow({
  label,
  description,
  enabled,
  onToggle,
}: {
  label: string;
  description?: string;
  enabled: boolean;
  onToggle: (next: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 px-4 py-3">
      <div className="min-w-0">
        <div className="text-sm font-medium text-text">{label}</div>
        {description ? (
          <div className="text-xs text-text-muted mt-0.5">{description}</div>
        ) : null}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        onClick={() => onToggle(!enabled)}
        className={cn(
          "relative h-6 w-10 shrink-0 rounded-full transition-colors",
          enabled ? "bg-primary" : "bg-surface-2",
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-surface shadow-card transition-transform",
            enabled ? "translate-x-4" : "translate-x-0",
          )}
        />
      </button>
    </div>
  );
}
