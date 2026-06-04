import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useMyAgents } from "@/api/endpoints/agents";
import { useAuth } from "@/store/auth";
import { ProfileTabs } from "@/design-system/components/ProfileTabs";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { TopBar } from "@/design-system/components/TopBar";
import { AddAgentCard } from "./components/AddAgentCard";
import { NewAgentForm } from "./components/NewAgentSheet";
import { ProfileEditCard } from "./components/ProfileEditCard";

/**
 * Figma profile Edit tab (node 2052:3082): the active agent's editable profile
 * card. The active agent is chosen from the TopBar agent dropdown; the
 * dropdown's "Add profile" navigates here with state to open a blank sheet.
 */
export function MyAgentsPage() {
  const { activeAgentId } = useAuth();
  const query = useMyAgents();
  const location = useLocation();
  const [newOpen, setNewOpen] = useState(false);

  // The New profile form is driven entirely by the createNew navigation flag.
  // "Add profile" sets it; picking an agent in the TopBar clears it (replace,
  // state: null) which closes the form and shows that agent's profile.
  useEffect(() => {
    const createNew = (location.state as { createNew?: boolean } | null)?.createNew === true;
    setNewOpen(createNew);
  }, [location.state]);

  return (
    <>
      <TopBar />
      <ProfileTabs />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-3">
        {newOpen ? (
          <NewAgentForm onClose={() => setNewOpen(false)} />
        ) : (
          <QueryBoundary query={query}>
            {(data) => {
              const agentId = activeAgentId ?? data.agents[0]?.agentId;
              if (!agentId) return <AddAgentCard />;
              return <ProfileEditCard agentId={agentId} />;
            }}
          </QueryBoundary>
        )}
      </div>
    </>
  );
}
