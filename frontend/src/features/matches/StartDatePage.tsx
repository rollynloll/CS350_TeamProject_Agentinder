import { useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useScheduleDate } from "@/api/endpoints/dates";
import { Avatar } from "@/design-system/components/Avatar";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { TierBadge } from "@/design-system/components/TierBadge";
import type { DateType, Tier } from "@/api/types";
import { cn } from "@/lib/cn";
import { nowLocalInput } from "@/lib/datetime";

type StartState = {
  partnerName?: string;
  partnerAvatarUrl?: string;
  tier?: Tier;
  myAvatarUrl?: string;
};

const dateTypes: Array<{ value: DateType; label: string }> = [
  { value: "coffee_chat", label: "Coffee Chat" },
  { value: "activity_date", label: "Activity Date" },
  { value: "deep_dive", label: "Deep Dive" },
];

/**
 * Figma 매칭-스타트데이트 (node 2052:2730): a full in-frame screen (not an
 * overlay) — the match cardsmall, Date Type chips, a Task field, and the
 * Start Date button.
 */
export function StartDatePage() {
  const { matchId } = useParams<{ matchId: string }>();
  const navigate = useNavigate();
  const s = (useLocation().state as StartState | null) ?? {};
  const schedule = useScheduleDate(matchId ?? "");

  const [type, setType] = useState<DateType>("coffee_chat");
  const [task, setTask] = useState("");
  const [time, setTime] = useState("");
  const minTime = useMemo(() => nowLocalInput(), []);

  const start = () => {
    if (!matchId || schedule.isPending) return;
    schedule.mutate(
      { type, proposedTime: time ? new Date(time).toISOString() : undefined, message: task || undefined },
      { onSuccess: () => navigate(`/conversations/${matchId}`) },
    );
  };

  return (
    <>
      <MobileHeader showBack title="Start Date" />
      <div className="flex-1 min-h-0 overflow-y-auto px-5 pt-2 pb-6 space-y-5">
        {/* Match cardsmall */}
        <div className="relative">
          <article className="flex items-center overflow-hidden rounded-[16px] bg-bg shadow-float">
            <Avatar
              src={s.partnerAvatarUrl}
              name={s.partnerName ?? "?"}
              size="lg"
              className="!w-[74px] !h-[74px] !rounded-none shrink-0"
            />
            <div className="flex flex-col gap-1 flex-1 min-w-0 px-3 py-2">
              <div className="flex items-center gap-2">
                <h3 className="flex-1 min-w-0 truncate text-body1 font-semibold text-text">
                  {s.partnerName ?? "Agent"}
                </h3>
                {s.tier ? <TierBadge tier={s.tier} className="min-w-[90px]" /> : null}
              </div>
              <div className="flex flex-col">
                <p className="text-caption text-text-muted leading-[1.4]">Status</p>
                <span className="text-caption font-semibold text-text">Awaiting</span>
              </div>
            </div>
          </article>
          {s.myAvatarUrl ? (
            <Avatar
              src={s.myAvatarUrl}
              name="me"
              size="sm"
              className="absolute -top-1.5 -left-1.5 z-10 !w-8 !h-8 ring-2 ring-bg"
            />
          ) : null}
        </div>

        {/* Date Type */}
        <div className="space-y-2">
          <h2 className="text-h3 font-semibold text-text">Date Type</h2>
          <div className="flex flex-wrap gap-2">
            {dateTypes.map((d) => (
              <button
                key={d.value}
                type="button"
                onClick={() => setType(d.value)}
                className={cn(
                  "rounded-full px-3 py-1.5 text-body2 font-semibold transition-all",
                  type === d.value
                    ? "bg-primary-light text-text"
                    : "bg-bg shadow-inset text-text-muted",
                )}
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>

        {/* Task */}
        <div className="space-y-2">
          <h2 className="text-h3 font-semibold text-text">Task</h2>
          <textarea
            value={task}
            onChange={(e) => setTask(e.target.value)}
            rows={5}
            placeholder="Describe your task."
            className="w-full resize-none rounded-[12px] bg-bg shadow-inset px-3 py-3 text-body2 leading-[1.4] text-text placeholder:text-text-subtle focus:outline-none"
          />
        </div>

        {/* Proposed time (from the original schedule flow) */}
        <div className="space-y-2">
          <h2 className="text-h3 font-semibold text-text">Proposed time</h2>
          <input
            type="datetime-local"
            value={time}
            min={minTime}
            onChange={(e) => setTime(e.target.value)}
            className="w-full rounded-[12px] bg-bg shadow-inset px-3 py-3 text-body1 text-text placeholder:text-text-subtle focus:outline-none"
          />
        </div>

        {/* Start Date */}
        <button
          type="button"
          onClick={start}
          disabled={schedule.isPending}
          className="w-full rounded-[12px] bg-primary py-3 text-body1 font-bold text-primary-fg disabled:opacity-60"
        >
          Start Date
        </button>
      </div>
    </>
  );
}
