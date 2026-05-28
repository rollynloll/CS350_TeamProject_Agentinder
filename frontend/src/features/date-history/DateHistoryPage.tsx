import { useParams } from "react-router-dom";
import { Star } from "lucide-react";
import { useMatchDates } from "@/api/endpoints/relationships";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { QueryBoundary } from "@/design-system/components/QueryBoundary";
import type { DateHistoryItem, DateType } from "@/api/types";

const typeLabel: Record<DateType, string> = {
  coffee_chat: "Coffee Chat",
  activity_date: "Activity Date",
  deep_dive: "Deep Dive",
};

export function DateHistoryPage() {
  const { matchId } = useParams<{ matchId: string }>();
  const query = useMatchDates(matchId);

  return (
    <QueryBoundary query={query}>
      {(data) => (
        <>
          <MobileHeader showBack title={data.match.partnerAgent.displayName} />
          <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-3">
            {data.dates.map((d) => (
              <DateHistoryCard key={d.dateId} item={d} />
            ))}
          </div>
        </>
      )}
    </QueryBoundary>
  );
}

function DateHistoryCard({ item }: { item: DateHistoryItem }) {
  const rating = item.mutualRating
    ? `${item.mutualRating.toFixed(1)}/5`
    : "rating";
  return (
    <article className="rounded-2xl bg-surface shadow-card p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-base font-bold tracking-tight">
          {typeLabel[item.type] ?? item.type}
        </h3>
        <span className="inline-flex items-center gap-1 rounded-full bg-surface-2 px-3 py-1 text-xs font-semibold text-text">
          <Star className="w-3.5 h-3.5" fill="currentColor" strokeWidth={0} />
          {rating}
        </span>
      </div>
      <div className="text-[11px] text-text-subtle font-medium">Result</div>
      <p className="text-sm text-text-muted leading-relaxed line-clamp-3">
        {item.summary}
      </p>
    </article>
  );
}
