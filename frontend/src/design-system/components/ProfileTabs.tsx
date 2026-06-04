import { NavLink, useLocation } from "react-router-dom";
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
  const location = useLocation();
  // While creating a new profile there is no agent to analyze yet, so the
  // Analytics / Relationship tabs are disabled (Edit stays active).
  const creatingNew =
    location.pathname === "/agents" &&
    (location.state as { createNew?: boolean } | null)?.createNew === true;

  // While creating a new profile there's no agent yet — show only Edit, and make
  // it an inert label (tapping it must not navigate to the real agent's Edit).
  if (creatingNew) {
    return (
      <div className="shrink-0 px-4 pt-1 pb-2">
        <div className="flex gap-1 p-1 rounded-full bg-bg shadow-inset">
          <span className="flex-1 text-center py-2 rounded-full text-body2 font-medium bg-surface shadow-float text-primary select-none">
            {t("nav.profile_edit")}
          </span>
        </div>
      </div>
    );
  }

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
