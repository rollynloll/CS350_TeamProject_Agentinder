import { useState, type FormEvent } from "react";
import { CornerDownLeft } from "lucide-react";
import { cn } from "@/lib/cn";
import { useKeyboardOpen } from "@/lib/useKeyboardOpen";
import { useVisualViewportBottom } from "@/lib/useVisualViewportBottom";

/**
 * Chat composer matching Figma Conversation/Chatting frames. Visual layer only —
 * the actual send mutation lands in a follow-up V1 interaction ticket.
 */
export function ChatInput({
  onSubmit,
  placeholder = "Type here",
  className,
}: {
  onSubmit?: (text: string) => void;
  placeholder?: string;
  className?: string;
}) {
  const [value, setValue] = useState("");
  const keyboardOpen = useKeyboardOpen();
  const vpBottom = useVisualViewportBottom();
  const docked = keyboardOpen && vpBottom !== null;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    onSubmit?.(trimmed);
    setValue("");
  };

  return (
    <form
      onSubmit={handleSubmit}
      // Dock above the keyboard via top + translateY(-100%) (iOS mis-positions
      // fixed `bottom` when the keyboard is up). Desktop never docks (no keyboard).
      style={docked ? { position: "fixed", left: 0, right: 0, top: vpBottom, transform: "translateY(-100%)" } : undefined}
      className={cn(
        "shrink-0 bg-bg px-3 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]",
        docked && "z-[60] pb-2 border-t border-border",
        className,
      )}
    >
      <div className="flex items-center gap-2 rounded-full bg-surface-2 pl-4 pr-1 py-1">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder}
          className="flex-1 bg-transparent text-body1 placeholder:text-text-subtle focus:outline-none py-2"
        />
        <button
          type="submit"
          aria-label="Send message"
          className="shrink-0 grid place-items-center w-9 h-9 rounded-full bg-surface text-text-subtle hover:text-primary transition-colors"
        >
          <CornerDownLeft className="w-4 h-4" />
        </button>
      </div>
    </form>
  );
}
