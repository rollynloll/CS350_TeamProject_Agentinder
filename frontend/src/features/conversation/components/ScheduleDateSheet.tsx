import { useMemo, useState, type FormEvent } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { Button } from "@/design-system/components/Button";
import { useKeyboard } from "@/design-system/components/keyboard-context";
import type { DateType } from "@/api/types";
import { cn } from "@/lib/cn";
import { nowLocalInput } from "@/lib/datetime";

// SRS UC-0301 step 2: offer the date types. REQ-0301: only Coffee Chat is
// supported in v1; Activity/Deep Dive are Phase 2.
const dateTypes: Array<{ value: DateType; label: string; note: string }> = [
  { value: "coffee_chat", label: "Coffee Chat", note: "Short text chat" },
  { value: "activity_date", label: "Activity Date", note: "Phase 2" },
  { value: "deep_dive", label: "Deep Dive", note: "Phase 2" },
];

export function ScheduleDateSheet({
  open,
  onOpenChange,
  onSubmit,
  submitting,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: { type: DateType; proposedTime: string }) => void;
  submitting?: boolean;
}) {
  const [type, setType] = useState<DateType>("coffee_chat");
  const [time, setTime] = useState("");
  const { height: kbHeight } = useKeyboard();
  const minTime = useMemo(() => nowLocalInput(), []);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!time) return;
    onSubmit({ type, proposedTime: time });
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/40 z-40 animate-in fade-in" />
        <Dialog.Content
          style={{ bottom: kbHeight }}
          className="fixed inset-x-0 z-50 bg-bg rounded-t-3xl border-t border-border max-h-[90dvh] overflow-y-auto transition-[bottom] duration-150 md:left-1/2 md:right-auto md:-translate-x-1/2 md:w-[393px]"
        >
          <form onSubmit={handleSubmit} className="p-5 space-y-5">
            <div className="flex items-start justify-between gap-2">
              <div>
                <Dialog.Title className="text-h3 font-bold">Schedule a date</Dialog.Title>
                <Dialog.Description className="text-body1 text-text-muted">
                  Propose a date type and time.
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <button
                  type="button"
                  aria-label="Close"
                  className="-mr-2 -mt-1 p-1.5 rounded-full text-text-muted hover:bg-surface-2"
                >
                  <X className="w-5 h-5" />
                </button>
              </Dialog.Close>
            </div>

            <div>
              <div className="text-body2 font-semibold text-text-muted mb-2">Type</div>
              <div className="grid grid-cols-3 gap-2">
                {dateTypes.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setType(opt.value)}
                    className={cn(
                      "rounded-xl border px-2 py-2 text-center transition-colors",
                      type === opt.value
                        ? "bg-primary text-primary-fg border-primary"
                        : "bg-surface text-text-muted border-border hover:bg-surface-2",
                    )}
                  >
                    <div className="text-body1 font-semibold">{opt.label}</div>
                    <div className="text-[10px] opacity-80">{opt.note}</div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label
                htmlFor="schedule-time"
                className="text-body2 font-semibold text-text-muted mb-2 block"
              >
                Proposed time
              </label>
              <input
                id="schedule-time"
                type="datetime-local"
                value={time}
                min={minTime}
                onChange={(e) => setTime(e.target.value)}
                className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-body1 text-text focus:outline-none focus:border-primary"
              />
            </div>

            <Button
              type="submit"
              size="lg"
              variant="pill"
              disabled={!time || submitting}
              className="w-full"
            >
              Propose date
            </Button>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
