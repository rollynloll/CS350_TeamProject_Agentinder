import { ALL_CAPABILITY_TAGS } from "@/features/agents/components/ProfileForm";
import { cn } from "@/lib/cn";

export function DiscoverFilters({
  selected,
  onChange,
}: {
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  const toggle = (tag: string) =>
    onChange(
      selected.includes(tag)
        ? selected.filter((t) => t !== tag)
        : [...selected, tag],
    );

  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-body1 font-semibold text-text">Capability Tags</div>
        <button
          type="button"
          onClick={() => onChange([])}
          className="text-body2 font-medium text-text-subtle hover:text-text"
        >
          Reset
        </button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {ALL_CAPABILITY_TAGS.map((tag) => {
          const isSelected = selected.includes(tag);
          return (
            <button
              key={tag}
              type="button"
              onClick={() => toggle(tag)}
              className={cn(
                "inline-flex items-center rounded-full px-3 py-1.5 text-body2 font-medium border transition-colors",
                isSelected
                  ? "bg-text text-bg border-text"
                  : "bg-surface text-text-muted border-border hover:bg-surface-2",
              )}
            >
              {tag}
            </button>
          );
        })}
      </div>
    </section>
  );
}
