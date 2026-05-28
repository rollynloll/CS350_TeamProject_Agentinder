import { useTranslation } from "react-i18next";
import { useActiveMatches, useApproveMatch, useRejectMatch } from "@/api/endpoints/matches";
import { useAuth } from "@/store/auth";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import { AgentMatchCard } from "./components/AgentMatchCard";

export function MatchesPage() {
  const { t } = useTranslation();
  const { activeAgentId } = useAuth();
  const query = useActiveMatches(activeAgentId ?? undefined);
  const approve = useApproveMatch();
  const reject = useRejectMatch();
  const deciding = approve.isPending || reject.isPending;

  return (
    <>
      <MobileHeader title={t("matches.title")} />
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-6">
        <QueryBoundary query={query}>
          {(data) =>
            data.sections.map((section) => (
              <section key={section.agentId} className="space-y-3">
                <h2 className="text-sm font-semibold text-text-muted">
                  {section.title}
                </h2>
                <div className="space-y-3">
                  {section.matches.map((m) => (
                    <AgentMatchCard
                      key={m.matchId}
                      match={m}
                      compatibilityScore={m.compatibilityScore}
                      deciding={deciding}
                      onApprove={() => approve.mutate(m.matchId)}
                      onReject={() => reject.mutate(m.matchId)}
                    />
                  ))}
                </div>
              </section>
            ))
          }
        </QueryBoundary>
      </div>
    </>
  );
}
