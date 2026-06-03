import { useNavigate, useParams } from "react-router-dom";
import { Star } from "lucide-react";
import { useMatchDates } from "@/api/endpoints/relationships";
import { Button } from "@/design-system/components/Button";
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
  const navigate = useNavigate();
  const query = useMatchDates(matchId);

  return (
    <QueryBoundary query={query}>
      {(data) => {
        // "Rate" opens the Date Result (show result) screen for that date.
        const openResult = () =>
          navigate(`/matches/${matchId}/result`, {
            state: {
              partnerName: data.match.partnerAgent.displayName,
              partnerAvatarUrl: data.match.partnerAgent.avatarUrl,
            },
          });
        return (
          <>
            <MobileHeader showBack title={data.match.partnerAgent.displayName} />
            <div className="flex-1 min-h-0 overflow-y-auto px-4 pt-2 pb-6 space-y-3">
              {data.dates.map((d) => (
                <DateHistoryCard key={d.dateId} item={d} onRate={openResult} />
              ))}
            </div>
          </>
        );
      }}
    </QueryBoundary>
  );
}

function DateHistoryCard({
  item,
  onRate,
}: {
  item: DateHistoryItem;
  onRate: () => void;
}) {
  const rating = item.mutualRating ? `${item.mutualRating.toFixed(1)}/5` : "rating";
  return (
    <article className="rounded-2xl bg-surface shadow-card p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-h3 font-bold tracking-tight">
          {typeLabel[item.type] ?? item.type}
        </h3>
        <span className="inline-flex items-center gap-1 rounded-full bg-surface-2 px-3 py-1 text-body2 font-semibold text-text">
          <Star className="w-3.5 h-3.5" fill="currentColor" strokeWidth={0} />
          {rating}
        </span>
      </div>
      <div className="text-[11px] text-text-subtle font-medium">Result</div>
      <p className="text-body1 text-text-muted leading-relaxed line-clamp-3">{item.summary}</p>
      {item.status === "completed" ? (
        <div className="flex justify-end pt-1">
          <Button size="sm" variant="secondary" onClick={onRate}>
            Rate
          </Button>
        </div>
      ) : null}
    </article>
  );
}
