import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * Centers the app inside a phone-shaped canvas. On mobile the canvas fills the
 * viewport height; on desktop it's a 393x852 frame in the center. Children
 * stack vertically (main + BottomNav) and the inner box clips overflow so that
 * sticky headers/footers stay pinned while only the middle scrolls.
 */
export function MobileShell({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className="flex-1 min-h-0 self-stretch md:bg-surface-2/40 md:py-6 md:px-4 flex justify-center overflow-hidden">
      <div
        className={cn(
          "relative w-full h-full flex flex-col bg-bg overflow-hidden",
          "md:w-[393px] md:h-[852px] md:max-h-[calc(100dvh-3rem)] md:rounded-[2rem] md:shadow-elevated md:border md:border-border",
          className,
        )}
      >
        {children}
      </div>
    </div>
  );
}
