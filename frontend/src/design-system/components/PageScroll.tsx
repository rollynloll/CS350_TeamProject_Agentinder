import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

/**
 * Default scrollable page body — flex-1 + overflow-y-auto + horizontal page
 * gutter. Use this for pages that don't have a sticky header/footer of their
 * own; pages that need full-bleed (ConversationPage, DateLivePage) bypass this
 * and arrange their own flex column directly inside <main>.
 */
export function PageScroll({
  className,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("flex-1 min-h-0 overflow-y-auto px-4 py-4", className)}
      {...rest}
    />
  );
}
