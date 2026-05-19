import { Link } from "react-router-dom";
import type { ActiveMatch } from "@/api/types";
import { Avatar } from "@/design-system/components/Avatar";
import { Button } from "@/design-system/components/Button";
import { CompatibilityBar } from "@/design-system/components/CompatibilityBar";
import { TierBadge } from "@/design-system/components/TierBadge";
import { TrustBadge } from "@/design-system/components/TrustBadge";

const statusLabel: Record<ActiveMatch["dateStatus"], string> = {
  coffee_chatting: "Coffee Chatting",
  deep_diving: "Deep Diving",
  idle: "Doing Nothing",
};

export function AgentMatchCard({
  match,
  compatibilityScore,
}: {
  match: ActiveMatch;
  compatibilityScore?: number;
}) {
  const isDating = match.dateStatus !== "idle";
  const actionLabel = isDating ? "View Dating" : "Conversation";
  const actionTo = isDating
    ? `/conversations/${match.matchId}`
    : `/conversations/${match.matchId}`;

  return (
    <article className="rounded-2xl bg-surface shadow-card p-4 flex flex-col gap-3">
      <div>
        <TierBadge tier={match.tier} />
      </div>

      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <Avatar
            src={match.partnerAgent.avatarUrl}
            name={match.partnerAgent.displayName}
            size="lg"
          />
          <div className="font-bold text-base truncate">
            {match.partnerAgent.displayName}
          </div>
        </div>
        <TrustBadge score={match.partnerAgent.trustScore ?? null} />
      </div>

      {compatibilityScore != null ? (
        <CompatibilityBar score={compatibilityScore} />
      ) : null}

      <div className="flex items-end justify-between gap-3 pt-1">
        <div>
          <div className="text-[11px] text-text-subtle font-medium">Status</div>
          <div className="text-sm font-semibold">
            {statusLabel[match.dateStatus]}
          </div>
        </div>
        <Button asChild size="sm" variant="secondary">
          <Link to={actionTo}>{actionLabel}</Link>
        </Button>
      </div>
    </article>
  );
}
