import { useTranslation } from "react-i18next";
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
      <MobileHeader title={t("agents.title")} />
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
