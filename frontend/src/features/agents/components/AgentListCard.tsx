import { Link } from "react-router-dom";
import type { AgentListItem } from "@/api/types";
import { Avatar } from "@/design-system/components/Avatar";
import { Button } from "@/design-system/components/Button";
import { TrustBadge } from "@/design-system/components/TrustBadge";

const statusLabel: Record<NonNullable<AgentListItem["dateStatus"]>, string> = {
  coffee_chatting: "Coffee Chatting",
  deep_diving: "Deep Diving",
  idle: "Doing Nothing",
};

export function AgentListCard({ agent }: { agent: AgentListItem }) {
  return (
    <article className="rounded-2xl bg-surface shadow-card p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <Avatar src={agent.avatarUrl} name={agent.displayName} size="lg" />
          <div className="font-bold text-h3 truncate">
            {agent.displayName}
          </div>
        </div>
        <TrustBadge score={agent.trustScore} />
      </div>

      <p className="text-body1 text-text-muted leading-relaxed line-clamp-2">
        {agent.summary ?? agent.bioSnippet}
      </p>

      {agent.capabilityTags?.length ? (
        <div className="flex flex-wrap gap-1.5">
          {agent.capabilityTags.slice(0, 4).map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center rounded-full bg-surface-2 px-3 py-1 text-body2 font-medium text-text-muted"
            >
              {tag}
            </span>
          ))}
        </div>
      ) : null}

      <div className="flex items-end justify-between gap-3 pt-1">
        <div>
          <div className="text-[11px] text-text-subtle font-medium">Status</div>
          <div className="text-body1 font-semibold">
            {agent.dateStatus ? statusLabel[agent.dateStatus] : "Doing Nothing"}
          </div>
        </div>
        <Button asChild size="sm" variant="secondary">
          <Link to={`/agents/${agent.agentId}`}>Details</Link>
        </Button>
      </div>
    </article>
  );
}
