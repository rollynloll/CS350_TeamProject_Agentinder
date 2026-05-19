import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * Centers the app inside a 393px phone-shaped canvas on desktop;
 * on mobile, fills the viewport. Children scroll inside this frame.
 */
export function MobileShell({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className="flex-1 md:bg-surface-2/40 md:py-6 md:px-4 flex justify-center min-h-0">
      <div
        className={cn(
          "relative w-full flex flex-col bg-bg overflow-hidden",
          "md:w-[393px] md:h-[852px] md:max-h-[calc(100dvh-3rem)] md:rounded-[2rem] md:shadow-elevated md:border md:border-border",
          className,
        )}
      >
        {children}
      </div>
    </div>
  );
}
