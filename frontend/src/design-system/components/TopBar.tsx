import { Link, useLocation, useNavigate } from "react-router-dom";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ChevronDown, ImagePlus, Plus, Settings as SettingsIcon } from "lucide-react";
import { useMyAgents } from "@/api/endpoints/agents";
import { useAuth } from "@/store/auth";
import { Avatar } from "./Avatar";
import { NotificationButton } from "./NotificationButton";
import { cn } from "@/lib/cn";

/**
 * Figma top bar shared by Home (2025:873) and Search (2051:1455): the
 * active-agent selector dropdown on the left (currentProfile), notifications +
 * settings gear on the right. Selecting an agent sets it active for the feed.
 */
export function TopBar() {
  const { activeAgentId, setActiveAgent } = useAuth();
  const { data } = useMyAgents();
  const agents = data?.agents ?? [];
  const active = agents.find((a) => a.agentId === activeAgentId) ?? agents[0];
  const location = useLocation();
  const navigate = useNavigate();
  const creatingNew =
    location.pathname === "/agents" &&
    (location.state as { createNew?: boolean } | null)?.createNew === true;
  const label = creatingNew ? "New profile" : (active?.displayName ?? "No agent");

  return (
    <header className="shrink-0 flex items-center justify-between gap-2 px-5 pt-4 pb-2">
      <DropdownMenu.Root>
        <DropdownMenu.Trigger asChild>
          <button
            type="button"
            className="flex items-center gap-2 rounded-full pr-2 text-text outline-none"
            aria-label="Switch active agent"
          >
            {creatingNew ? (
              <span className="grid place-items-center w-7 h-7 rounded-full bg-surface-2 text-text-muted">
                <ImagePlus className="w-4 h-4" strokeWidth={1.75} />
              </span>
            ) : (
              <Avatar
                src={active?.avatarUrl}
                name={active?.displayName ?? "?"}
                size="sm"
                className="!w-7 !h-7"
              />
            )}
            <span className="text-h3 font-semibold truncate max-w-[140px]">
              {label}
            </span>
            <ChevronDown className="w-5 h-5 text-text-muted" strokeWidth={2} />
          </button>
        </DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content
            align="start"
            sideOffset={8}
            className="z-50 min-w-[200px] rounded-xl bg-surface shadow-elevated border border-border p-1.5"
          >
            {agents.map((a) => (
              <DropdownMenu.Item
                key={a.agentId}
                onSelect={() => {
                  setActiveAgent(a.agentId);
                  // Clear the createNew flag so the label/form leave "New profile".
                  if (creatingNew) navigate("/agents", { replace: true, state: null });
                }}
                className={cn(
                  "flex items-center gap-2 px-2 py-2 rounded-lg text-body1 cursor-pointer outline-none",
                  "data-[highlighted]:bg-bg",
                  a.agentId === active?.agentId ? "text-primary" : "text-text",
                )}
              >
                <Avatar src={a.avatarUrl} name={a.displayName} size="sm" className="!w-6 !h-6" />
                <span className="truncate">{a.displayName}</span>
              </DropdownMenu.Item>
            ))}
            <DropdownMenu.Item asChild>
              <Link
                to="/agents"
                state={{ createNew: true }}
                className="flex items-center gap-2 px-2 py-2 rounded-lg text-body1 text-primary cursor-pointer outline-none data-[highlighted]:bg-bg"
              >
                <span className="grid place-items-center w-6 h-6 rounded-full bg-bg shadow-inset text-primary">
                  <Plus className="w-4 h-4" strokeWidth={2.5} />
                </span>
                Add profile
              </Link>
            </DropdownMenu.Item>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>

      <div className="flex items-center gap-2">
        <NotificationButton />
        <Link
          to="/settings"
          aria-label="Open settings"
          className="grid place-items-center w-11 h-11 rounded-full text-text hover:bg-surface transition-colors"
        >
          <SettingsIcon className="w-6 h-6" strokeWidth={1.75} />
        </Link>
      </div>
    </header>
  );
}
