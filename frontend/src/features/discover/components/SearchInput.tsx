import { Search } from "lucide-react";
import { cn } from "@/lib/cn";

export function SearchInput({
  value,
  onChange,
  onSubmit,
  placeholder = "Search agents",
  className,
}: {
  value: string;
  onChange: (next: string) => void;
  onSubmit?: (value: string) => void;
  placeholder?: string;
  className?: string;
}) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit?.(value);
      }}
      className={cn(
        "shrink-0 bg-bg px-3 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]",
        className,
      )}
    >
      <div className="flex items-center gap-2 rounded-full bg-surface shadow-card pl-4 pr-3 py-1">
        <input
          type="search"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          aria-label="Search agents"
          className="flex-1 bg-transparent text-sm placeholder:text-text-subtle focus:outline-none py-2.5"
        />
        <Search className="w-5 h-5 text-text-subtle shrink-0" strokeWidth={1.75} />
      </div>
    </form>
  );
}
