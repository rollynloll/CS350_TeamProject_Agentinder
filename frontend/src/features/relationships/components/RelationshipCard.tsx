import { Link } from "react-router-dom";
import type { RelationshipItem } from "@/api/types";
import { Avatar } from "@/design-system/components/Avatar";
import { TierBadge } from "@/design-system/components/TierBadge";

/**
 * Figma profile-relationship `cardsmall` (node 2061:1235): avatar + name +
 * tierBadge, with a Status row whose action links to the date history.
 */
export function RelationshipCard({ item }: { item: RelationshipItem }) {
  return (
    <article className="flex items-center overflow-hidden rounded-[16px] bg-bg shadow-float">
      <Avatar
        src={item.partnerAgent.avatarUrl}
        name={item.partnerAgent.displayName}
        size="lg"
        className="!w-[74px] !h-[74px] !rounded-none shrink-0"
      />
      <div className="flex flex-col gap-1 flex-1 min-w-0 px-3 py-2">
        <div className="flex items-center gap-2">
          <h3 className="flex-1 min-w-0 truncate text-body1 font-semibold text-text">
            {item.partnerAgent.displayName}
          </h3>
          <TierBadge tier={item.tier} className="min-w-[90px]" />
        </div>

        <div className="flex flex-col">
          <p className="text-caption text-text-muted leading-[1.4]">
            {item.totalDates} dates · ★ {item.mutualRating.toFixed(1)}
          </p>
          <div className="flex items-center justify-between gap-2">
            <span className="text-caption font-semibold text-text truncate">
              {item.lastDateSummary}
            </span>
            <Link
              to={`/matches/${item.matchId}/history`}
              className="inline-flex items-center justify-center min-w-[90px] shrink-0 rounded-[8px] bg-primary-light px-2 py-1 text-caption font-semibold text-text"
            >
              View History
            </Link>
          </div>
        </div>
      </div>
    </article>
  );
}
