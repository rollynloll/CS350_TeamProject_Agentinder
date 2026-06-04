import { useState } from "react";
import { Bell, Heart, Network, ShieldCheck, Sparkles } from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Figma `notice` component (default / new variants): bell with a red dot when
 * there are unread notifications. Tapping it opens an in-frame panel listing
 * one of each notification kind that Settings → Notification can toggle:
 * New Match / Date Done / Trust Score Change / Relationship Change.
 */
type Notice = { icon: LucideIcon; title: string; body: string };

const NOTICES: Notice[] = [
  { icon: Sparkles, title: "New Match", body: "It's a match! You and Scheduler want to meet." },
  { icon: Heart, title: "Date Done", body: "Your Date with Mathematician is complete." },
  {
    icon: ShieldCheck,
    title: "Trust Score Change",
    body: "Scheduler's trust score rose to 0.92.",
  },
  {
    icon: Network,
    title: "Relationship Change",
    body: "Economist is now your Acquaintance.",
  },
];

export function NotificationButton({ className }: { className?: string }) {
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(true);

  return (
    <>
      <button
        type="button"
        aria-label="Notifications"
        onClick={() => {
          setOpen((o) => !o);
          setUnread(false);
        }}
        className={
          className ??
          "relative grid place-items-center w-11 h-11 rounded-full text-text hover:bg-surface transition-colors"
        }
      >
        <Bell className="w-6 h-6" strokeWidth={1.75} />
        {unread ? (
          <span className="absolute top-2.5 right-2.5 w-2 h-2 rounded-full bg-danger ring-2 ring-bg" />
        ) : null}
      </button>

      {open ? (
        <>
          <div className="absolute inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-3 top-[60px] z-50 w-[300px] max-w-[calc(100%-24px)] rounded-2xl bg-surface shadow-elevated border border-border p-2">
            <p className="px-2 py-1 text-body2 font-semibold text-text-muted">Notifications</p>
            <div className="flex flex-col">
              {NOTICES.map((n) => (
                <div key={n.title} className="flex items-start gap-3 px-2 py-2 rounded-xl">
                  <span className="grid place-items-center w-9 h-9 shrink-0 rounded-full bg-bg shadow-inset text-primary">
                    <n.icon className="w-[18px] h-[18px]" strokeWidth={2} />
                  </span>
                  <div className="min-w-0">
                    <p className="text-body2 font-semibold text-text">{n.title}</p>
                    <p className="text-caption leading-[1.4] text-text-muted">{n.body}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : null}
    </>
  );
}
