import { useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { Check, Star } from "lucide-react";
import { Avatar } from "@/design-system/components/Avatar";
import { MobileHeader } from "@/design-system/components/MobileHeader";
import { TierBadge } from "@/design-system/components/TierBadge";
import type { Tier } from "@/api/types";
import { cn } from "@/lib/cn";
import { useEndDate } from "@/api/endpoints/dates";

type ResultState = {
  dateId?: string;
  partnerAgentId?: string;
  partnerName?: string;
  partnerAvatarUrl?: string;
  tier?: Tier;
  myAvatarUrl?: string;
};

const ISSUES = ["Hallucination", "Latency", "Unresponsive", "Unauthorized Behavior"] as const;

/**
 * Figma 매칭-결과보기 (node 2052:2912): an in-frame Date Result screen (not an
 * overlay) — match cardsmall, Date Summary, Transcript, star Rating,
 * Compatibility slider, Comment, and the Issues checklist with a Save action.
 */
export function DateResultPage() {
  const { matchId } = useParams<{ matchId: string }>();
  const navigate = useNavigate();
  const s = (useLocation().state as ResultState | null) ?? {};

  const [rating, setRating] = useState(0);
  const [compat, setCompat] = useState(50);
  const [comment, setComment] = useState("");
  const [issues, setIssues] = useState<Set<string>>(new Set());

  const endDate = useEndDate(s.dateId ?? "");

  const toggleIssue = (i: string) =>
    setIssues((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });

  const save = () => {
    if (s.dateId && rating > 0) {
      endDate.mutate(
        {
          outcome: "completed",
          rating,
          compatibility: compat,
          ratedAgentId: s.partnerAgentId,
        },
        { onSettled: () => navigate(`/matches/${matchId}/history`, { state: s }) },
      );
    } else {
      navigate(`/matches/${matchId}/history`, { state: s });
    }
  };

  return (
    <>
      <MobileHeader
        showBack
        title="Date Result"
        action={
          <button
            type="button"
            onClick={save}
            className="rounded-[8px] bg-primary-light px-3 py-1 text-body2 font-semibold text-text"
          >
            Save
          </button>
        }
      />
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
                <span className="text-caption font-semibold text-text">Done</span>
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

        {/* Date Summary */}
        <Section title="Date Summary">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="rounded-full bg-bg shadow-inset px-3 py-1 text-body2 font-semibold text-text">
              Coffee Chat
            </span>
            <span className="text-body2 text-text-muted">Mar 12, 2:10 PM – 3:16 PM</span>
          </div>
        </Section>

        {/* Transcript */}
        <Section title="Transcript">
          <p className="text-body2 leading-[1.4] text-text-muted">
            Coordinated a meeting schedule between two teams across different time zones, resolving
            3 conflicts and finalizing a weekly sync plan.
          </p>
          <button type="button" className="text-body2 font-semibold text-primary self-start">
            View full Transcript
          </button>
        </Section>

        {/* Rating */}
        <Section title="Rating">
          <div className="flex items-center gap-2">
            {[1, 2, 3, 4, 5].map((n) => (
              <button key={n} type="button" onClick={() => setRating(n)} aria-label={`${n} star`}>
                <Star
                  className={cn("w-6 h-6", n <= rating ? "text-warning" : "text-text-subtle/40")}
                  fill={n <= rating ? "currentColor" : "none"}
                  strokeWidth={1.5}
                />
              </button>
            ))}
          </div>
        </Section>

        {/* Compatibility */}
        <Section title="Compatibility">
          <div className="relative h-4 flex items-center">
            <div className="absolute inset-x-0 h-1 rounded-full bg-text-muted/20" />
            <div
              className="absolute left-0 h-1 rounded-full bg-primary"
              style={{ width: `${compat}%` }}
            />
            <span
              className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 h-4 w-4 rounded-full bg-primary-light shadow-float pointer-events-none"
              style={{ left: `${compat}%` }}
            />
            <input
              type="range"
              min={0}
              max={100}
              value={compat}
              onChange={(e) => setCompat(Number(e.target.value))}
              aria-label="Compatibility"
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
          </div>
        </Section>

        {/* Comment */}
        <Section title="Comment">
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={4}
            placeholder="Leave your comment."
            className="w-full resize-none rounded-[12px] bg-bg shadow-inset px-3 py-3 text-body2 leading-[1.4] text-text placeholder:text-text-subtle focus:outline-none"
          />
        </Section>

        {/* Issues */}
        <Section title="Issues">
          <div className="flex flex-col gap-3">
            {ISSUES.map((i) => {
              const on = issues.has(i);
              return (
                <button
                  key={i}
                  type="button"
                  onClick={() => toggleIssue(i)}
                  className="flex items-center justify-between"
                >
                  <span className="text-body1 text-text">{i}</span>
                  <span
                    className={cn(
                      "grid place-items-center w-6 h-6 rounded-md transition-colors",
                      on ? "bg-primary text-primary-fg" : "bg-bg shadow-inset text-transparent",
                    )}
                  >
                    <Check className="w-4 h-4" strokeWidth={3} />
                  </span>
                </button>
              );
            })}
          </div>
        </Section>
      </div>
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-h3 font-semibold text-text">{title}</h2>
      {children}
    </section>
  );
}
