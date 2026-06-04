import { useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { isStandalone } from "@/lib/standalone";
import { StatusBar } from "@/design-system/components/StatusBar";

/**
 * Centers the app inside a phone-shaped canvas. On mobile the canvas fills the
 * viewport height; on desktop it's a 393x852 frame in the center. The Figma iOS
 * status bar pins to the top; children stack below and the inner box clips
 * overflow so only the middle scrolls. The Discover search / chat composer dock
 * above the on-screen keyboard via fixed positioning (iOS pins fixed elements to
 * the visual-viewport bottom).
 */
export function MobileShell({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  // Installed PWA: the OS draws the real status bar, so drop the mock one and
  // reserve the top safe-area inset instead (avoids overlapping the OS clock).
  const [standalone] = useState(isStandalone);

  return (
    <div className="flex-1 min-h-0 self-stretch md:bg-surface-2/40 md:py-6 md:px-4 flex justify-center overflow-hidden">
      <div
        className={cn(
          "relative w-full h-full flex flex-col bg-bg overflow-hidden",
          "md:w-[393px] md:h-[852px] md:max-h-[calc(100dvh-3rem)] md:rounded-[2rem] md:shadow-elevated md:border md:border-border",
          standalone && "pt-[env(safe-area-inset-top)]",
          className,
        )}
      >
        {standalone ? null : <StatusBar />}
        {children}
      </div>
    </div>
  );
}
