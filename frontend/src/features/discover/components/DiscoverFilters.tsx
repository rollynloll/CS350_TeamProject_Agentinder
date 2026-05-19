import { useState } from "react";
import { ALL_CAPABILITY_TAGS } from "@/features/agents/components/ProfileForm";
import { cn } from "@/lib/cn";

export function DiscoverFilters() {
  const [selected, setSelected] = useState<string[]>(["Optimize", "Plan"]);

  const toggle = (tag: string) =>
    setSelected((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );

  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-text">Capability Tags</div>
        <button
          type="button"
          onClick={() => setSelected([])}
          className="text-xs font-medium text-text-subtle hover:text-text"
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
                "inline-flex items-center rounded-full px-3 py-1.5 text-xs font-medium border transition-colors",
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
