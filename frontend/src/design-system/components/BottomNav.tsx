import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Home, MessageSquare, Search, User } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";

type Tab = {
  to: string;
  icon: LucideIcon;
  i18nKey: "my_page" | "home" | "chat" | "search";
  isActive: (pathname: string) => boolean;
};

const tabs: Tab[] = [
  {
    to: "/agents",
    icon: User,
    i18nKey: "my_page",
    isActive: (p) =>
      p.startsWith("/agents") ||
      p.startsWith("/relationships") ||
      p.startsWith("/analytics") ||
      p.startsWith("/settings"),
  },
  { to: "/", icon: Home, i18nKey: "home", isActive: (p) => p === "/" },
  {
    to: "/matches",
    icon: MessageSquare,
    i18nKey: "chat",
    isActive: (p) =>
      p.startsWith("/matches") ||
      p.startsWith("/conversations") ||
      p.startsWith("/dates"),
  },
  {
    to: "/discover",
    icon: Search,
    i18nKey: "search",
    isActive: (p) => p.startsWith("/discover"),
  },
];

export function BottomNav() {
  const { t } = useTranslation();
  const { pathname } = useLocation();

  return (
    <nav
      aria-label="Primary"
      className="shrink-0 bg-surface border-t border-border px-2 pt-1.5 pb-[max(0.5rem,env(safe-area-inset-bottom))]"
    >
      <ul className="flex items-center justify-around">
        {tabs.map(({ to, icon: Icon, i18nKey, isActive }) => {
          const active = isActive(pathname);
          return (
            <li key={to} className="flex-1">
              <Link
                to={to}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex flex-col items-center justify-center gap-0.5 py-1.5 rounded-lg text-[10px] font-medium transition-colors",
                  active ? "text-primary" : "text-text-subtle",
                )}
              >
                <Icon
                  className="w-6 h-6"
                  fill={active ? "currentColor" : "none"}
                  strokeWidth={active ? 1.5 : 2}
                />
                <span>{t(`nav.${i18nKey}`)}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
