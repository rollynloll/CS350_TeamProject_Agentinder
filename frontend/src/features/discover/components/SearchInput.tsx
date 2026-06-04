import { Search } from "lucide-react";
import { cn } from "@/lib/cn";
import { useKeyboardOpen } from "@/lib/useKeyboardOpen";
import { useVisualViewportBottom } from "@/lib/useVisualViewportBottom";

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
  const keyboardOpen = useKeyboardOpen();
  const vpBottom = useVisualViewportBottom();
  const docked = keyboardOpen && vpBottom !== null;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit?.(value);
      }}
      // Dock above the keyboard via top + translateY(-100%) (iOS mis-positions
      // fixed `bottom` when the keyboard is up). Desktop never docks (no keyboard).
      style={docked ? { position: "fixed", left: 0, right: 0, top: vpBottom, transform: "translateY(-100%)" } : undefined}
      className={cn(
        "shrink-0 bg-bg px-3 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]",
        docked && "z-[60] pb-2 border-t border-border",
        className,
      )}
    >
      <div className="flex items-center gap-2 rounded-full bg-bg shadow-inset pl-3 pr-4 py-1">
        <Search className="w-4 h-4 text-text-subtle shrink-0" strokeWidth={2} />
        <input
          type="search"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          aria-label="Search agents"
          className="flex-1 bg-transparent text-body1 placeholder:text-text-subtle focus:outline-none py-2"
        />
      </div>
    </form>
  );
}
