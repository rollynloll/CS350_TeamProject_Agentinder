import { useState } from "react";
import { Search } from "lucide-react";
import { useKeyboard } from "@/design-system/components/keyboard-context";
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
  const { open, height } = useKeyboard();
  const [focused, setFocused] = useState(false);
  // While typing, dock the field directly above the keyboard.
  const docked = open && focused;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit?.(value);
      }}
      style={docked ? { bottom: height } : undefined}
      className={cn(
        "shrink-0 bg-bg px-3 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]",
        docked && "absolute inset-x-0 z-[60] pb-2 border-t border-border",
        className,
      )}
    >
      <div className="flex items-center gap-2 rounded-full bg-bg shadow-inset pl-3 pr-4 py-1">
        <Search className="w-4 h-4 text-text-subtle shrink-0" strokeWidth={2} />
        <input
          type="search"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={placeholder}
          aria-label="Search agents"
          className="flex-1 bg-transparent text-body1 placeholder:text-text-subtle focus:outline-none py-2"
        />
      </div>
    </form>
  );
}
