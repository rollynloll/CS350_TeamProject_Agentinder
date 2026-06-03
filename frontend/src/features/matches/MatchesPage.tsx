import { Link } from "react-router-dom";
import { Settings as SettingsIcon } from "lucide-react";
import { useActiveMatches } from "@/api/endpoints/matches";
import { useMyAgents } from "@/api/endpoints/agents";
import { useAuth } from "@/store/auth";
import { EmptyState } from "@/design-system/components/EmptyState";
import { NotificationButton } from "@/design-system/components/NotificationButton";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { AgentMatchCard } from "./components/AgentMatchCard";
import type { ActiveMatch } from "@/api/types";

type Row = ActiveMatch & { myAvatarUrl?: string };

export function MatchesPage() {
  const { activeAgentId } = useAuth();
  const query = useActiveMatches(activeAgentId ?? undefined);
  const { data: agents } = useMyAgents();

  const avatarOf = (agentId: string) =>
    agents?.agents.find((a) => a.agentId === agentId)?.avatarUrl;

  return (
    <>
      <header className="shrink-0 flex items-center justify-end gap-1 px-5 pt-4 pb-1">
        <NotificationButton />
        <Link
          to="/settings"
          aria-label="Open settings"
          className="grid place-items-center w-11 h-11 rounded-full text-text hover:bg-surface transition-colors"
        >
          <SettingsIcon className="w-6 h-6" strokeWidth={1.75} />
        </Link>
      </header>

      <div className="flex-1 min-h-0 overflow-y-auto px-5 pt-1 pb-6 space-y-6">
        <QueryBoundary query={query}>
          {(data) => {
            const all: Row[] = data.sections.flatMap((s) =>
              s.matches.map((m) => ({ ...m, myAvatarUrl: avatarOf(s.agentId) })),
            );
            const active = all.filter((m) => m.approvalStatus !== "rejected");
            const past = all.filter((m) => m.approvalStatus === "rejected");

            if (all.length === 0) {
              return (
                <EmptyState
                  title="아직 매치가 없어요"
                  description="피드에서 다른 에이전트를 스와이프하면, 상대도 관심을 보일 때 매치가 생성됩니다."
                />
              );
            }

            return (
              <>
                <section className="space-y-3">
                  <h2 className="text-h2 font-bold text-text">Active Matches</h2>
                  {active.map((m) => (
                    <AgentMatchCard key={m.matchId} match={m} myAvatarUrl={m.myAvatarUrl} />
                  ))}
                </section>

                {past.length > 0 ? (
                  <section className="space-y-3">
                    <h2 className="text-h2 font-bold text-text">Past Matches</h2>
                    {past.map((m) => (
                      <AgentMatchCard key={m.matchId} match={m} myAvatarUrl={m.myAvatarUrl} />
                    ))}
                  </section>
                ) : null}
              </>
            );
          }}
        </QueryBoundary>
      </div>
    </>
  );
}
