import { Link, useLocation } from "react-router-dom";
import { Home, MessageSquare, Search, User } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";
import { useKeyboardOpen } from "@/lib/useKeyboardOpen";

type Tab = {
  to: string;
  icon: LucideIcon;
  label: string;
  isActive: (pathname: string) => boolean;
};

// Figma navigation_bar (node 2025:1098): icon-only, order home/search/chat/profile.
const tabs: Tab[] = [
  { to: "/", icon: Home, label: "Home", isActive: (p) => p === "/" },
  {
    to: "/discover",
    icon: Search,
    label: "Search",
    isActive: (p) => p.startsWith("/discover"),
  },
  {
    to: "/matches",
    icon: MessageSquare,
    label: "Chat",
    isActive: (p) =>
      p.startsWith("/matches") ||
      p.startsWith("/conversations") ||
      p.startsWith("/dates"),
  },
  {
    to: "/agents",
    icon: User,
    label: "Profile",
    isActive: (p) =>
      p.startsWith("/agents") ||
      p.startsWith("/relationships") ||
      p.startsWith("/analytics") ||
      p.startsWith("/settings"),
  },
];

/**
 * Figma bottom nav (Rectangle 59 + navigation_bar): a 90px bar, four 44px
 * icon-only tabs spread across it (no text labels), active filled / inactive
 * muted outline.
 */
export function BottomNav() {
  const { pathname } = useLocation();
  const keyboardOpen = useKeyboardOpen();

  return (
    <nav
      aria-label="Primary"
      // Mobile: fixed to the viewport bottom so the keyboard overlays it and it
      // can't ride up with the focused input. Desktop: back in the frame's flow.
      // Height includes the iOS home-indicator safe area so the bar's background
      // reaches the very bottom of the screen in standalone (Add to Home Screen).
      // When the keyboard is up, hide the bar on mobile (desktop keeps it).
      className={cn(
        "fixed inset-x-0 bottom-0 z-30 md:static md:z-auto shrink-0 h-[calc(64px+env(safe-area-inset-bottom))] bg-surface shadow-elevated flex items-start justify-between px-5 pt-3 pb-[env(safe-area-inset-bottom)]",
        keyboardOpen && "max-md:hidden",
      )}
    >
      {tabs.map(({ to, icon: Icon, label, isActive }) => {
        const active = isActive(pathname);
        return (
          <Link
            key={to}
            to={to}
            aria-label={label}
            aria-current={active ? "page" : undefined}
            className={cn(
              "grid place-items-center w-11 h-11 transition-colors",
              active ? "text-primary" : "text-text-subtle",
            )}
          >
            <Icon
              className="w-6 h-6"
              fill={active ? "currentColor" : "none"}
              strokeWidth={active ? 1.5 : 2}
            />
          </Link>
        );
      })}
    </nav>
  );
}
