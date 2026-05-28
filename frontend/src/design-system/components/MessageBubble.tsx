import { cn } from "@/lib/cn";

/**
 * Single chat bubble. Mine bubbles sit right-aligned in a peach tone; partner
 * bubbles sit left-aligned in surface white. Width is capped at 80% of the
 * conversation column so long messages wrap instead of edge-to-edge.
 */
export function MessageBubble({
  mine,
  children,
  className,
}: {
  mine: boolean;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex w-full", mine ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words shadow-card",
          mine ? "bg-danger-light text-text" : "bg-surface text-text",
          className,
        )}
      >
        {children}
      </div>
    </div>
  );
}
