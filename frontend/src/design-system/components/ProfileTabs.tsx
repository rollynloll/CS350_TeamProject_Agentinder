import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/cn";

/**
 * Figma Profile screen segmented control — Edit / Analytics / Relationship.
 * Replaces the old top-level Relationships + Analytics nav entries: those pages
 * now live as tabs under the Profile (My Agents) destination. Rendered just
 * below the page's MobileHeader on each of the three routes.
 */
const tabs = [
  { to: "/agents", key: "profile_edit" },
  { to: "/analytics", key: "profile_analytics" },
  { to: "/relationships", key: "profile_relationship" },
] as const;

export function ProfileTabs() {
  const { t } = useTranslation();

  return (
    <div className="shrink-0 px-4 pt-1 pb-2">
      <div className="flex gap-1 p-1 rounded-full bg-bg shadow-inset">
        {tabs.map(({ to, key }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/agents"}
            className={({ isActive }) =>
              cn(
                "flex-1 text-center py-2 rounded-full text-body2 font-medium transition-all",
                isActive
                  ? "bg-surface shadow-float text-primary"
                  : "text-text-muted hover:text-text",
              )
            }
          >
            {t(`nav.${key}`)}
          </NavLink>
        ))}
      </div>
    </div>
  );
}
