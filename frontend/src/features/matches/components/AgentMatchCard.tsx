import { useNavigate } from "react-router-dom";
import type { ActiveMatch } from "@/api/types";
import { Avatar } from "@/design-system/components/Avatar";
import { TierBadge } from "@/design-system/components/TierBadge";

type Cta = { label: string; cta: string; go: () => void };

/**
 * Figma matching `cardsmall` (node 2052:2198): partner avatar with MY matched
 * agent's avatar overlapping the top-left corner, name + tierBadge, and a
 * Status row whose action pill routes to the matching CTA destination:
 *   Dating          → View Date     → live date conversation
 *   Awaiting        → Start Date    → conversation + schedule sheet
 *   Deep Dive done  → Show Result   → date history / result
 *   Unmatched       → View History  → date history
 */
export function AgentMatchCard({
  match,
  myAvatarUrl,
}: {
  match: ActiveMatch;
  myAvatarUrl?: string;
}) {
  const navigate = useNavigate();
  const mid = match.matchId;

  const partnerState = {
    partnerName: match.partnerAgent.displayName,
    partnerAgentId: match.partnerAgent.agentId,
    partnerAvatarUrl: match.partnerAgent.avatarUrl,
    tier: match.tier,
    myAvatarUrl,
    dateId: match.latestDateId,
  };

  const view: Cta = {
    // Auto-formed matches are tagged so users can tell them from manual ones.
    label: match.matchType === "auto" ? "Dating(Auto)" : "Dating",
    cta: match.matchType === "auto" ? "View Date" : "Chat",
    go: () => navigate(`/conversations/${mid}`, { state: partnerState }),
  };
  const start: Cta = {
    label: "Awaiting",
    cta: "Start Date",
    go: () => navigate(`/matches/${mid}/start`, { state: partnerState }),
  };
  const show: Cta = {
    label: "Done",
    cta: "Show Result",
    go: () => navigate(`/matches/${mid}/result`, { state: partnerState }),
  };
  const history: Cta = {
    label: "Unmatched",
    cta: "View History",
    go: () => navigate(`/matches/${mid}/history`),
  };

  const action: Cta =
    match.approvalStatus === "rejected"
      ? history
      : match.dateStatus === "coffee_chatting"
        ? view
        : match.dateStatus === "deep_diving"
          ? show
          : start;

  return (
    <div className="relative">
      <article className="flex items-center overflow-hidden rounded-[16px] bg-bg shadow-float">
        <Avatar
          src={match.partnerAgent.avatarUrl}
          name={match.partnerAgent.displayName}
          size="lg"
          className="!w-[74px] !h-[74px] !rounded-none shrink-0"
        />
        <div className="flex flex-col gap-1 flex-1 min-w-0 px-3 py-2">
          <div className="flex items-center gap-2">
            <h3 className="flex-1 min-w-0 truncate text-body1 font-semibold text-text">
              {match.partnerAgent.displayName}
            </h3>
            <TierBadge tier={match.tier} className="min-w-[90px]" />
          </div>

          <div className="flex flex-col">
            <p className="text-caption text-text-muted leading-[1.4]">Status</p>
            <div className="flex items-center justify-between gap-2">
              <span className="text-caption font-semibold text-text whitespace-nowrap">
                {action.label}
              </span>
              <button
                type="button"
                onClick={action.go}
                className="inline-flex items-center justify-center min-w-[90px] rounded-[8px] bg-primary-light px-2 py-1 text-caption font-semibold text-text"
              >
                {action.cta}
              </button>
            </div>
          </div>
        </div>
      </article>

      {/* My matched agent's avatar, overlapping the top-left corner */}
      {myAvatarUrl !== undefined ? (
        <Avatar
          src={myAvatarUrl}
          name="me"
          size="sm"
          className="absolute -top-1.5 -left-1.5 z-10 !w-8 !h-8 ring-2 ring-bg"
        />
      ) : null}
    </div>
  );
}
