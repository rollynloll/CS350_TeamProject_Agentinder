import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Settings as SettingsIcon } from "lucide-react";
import { useMyAgents } from "@/api/endpoints/agents";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { AddAgentCard } from "./components/AddAgentCard";
import { AgentListCard } from "./components/AgentListCard";

export function MyAgentsPage() {
  const { t } = useTranslation();
  const query = useMyAgents();

  return (
    <>
      <MobileHeader
        title={t("agents.title")}
        action={
          <Link
            to="/settings"
            aria-label="Open settings"
            className="grid place-items-center w-9 h-9 rounded-full text-text hover:bg-surface-2 transition-colors"
          >
            <SettingsIcon className="w-5 h-5" strokeWidth={1.75} />
          </Link>
        }
      />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-3">
        <QueryBoundary query={query}>
          {(data) => (
            <>
              {data.agents.map((agent) => (
                <AgentListCard key={agent.agentId} agent={agent} />
              ))}
              <AddAgentCard />
            </>
          )}
        </QueryBoundary>
      </div>
    </>
  );
}
