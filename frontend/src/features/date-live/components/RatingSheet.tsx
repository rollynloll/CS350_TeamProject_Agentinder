import { useState, type FormEvent } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Star, X } from "lucide-react";
import { Button } from "@/design-system/components/Button";
import { useKeyboard } from "@/design-system/components/keyboard-context";
import { cn } from "@/lib/cn";

type Outcome = "successful" | "neutral" | "unsuccessful";

const outcomeOptions: Array<{ value: Outcome; label: string }> = [
  { value: "successful", label: "Successful" },
  { value: "neutral", label: "Neutral" },
  { value: "unsuccessful", label: "Unsuccessful" },
];

export function RatingSheet({
  open,
  onOpenChange,
  partnerName,
  onSubmit,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  partnerName: string;
  onSubmit?: (data: {
    rating: number;
    outcome: Outcome;
    feedback: string;
    compatibility: number;
  }) => void;
}) {
  const [rating, setRating] = useState(0);
  const [outcome, setOutcome] = useState<Outcome>("neutral");
  const [feedback, setFeedback] = useState("");
  const [compatibility, setCompatibility] = useState(3);
  const { height: kbHeight } = useKeyboard();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (rating === 0) return;
    onSubmit?.({ rating, outcome, feedback, compatibility });
    onOpenChange(false);
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Overlay className="absolute inset-0 bg-black/50 z-40" />
      <Dialog.Content
        style={{ bottom: kbHeight }}
        className="absolute inset-x-0 top-[59px] z-50 bg-bg rounded-t-3xl border-t border-border overflow-y-auto transition-[bottom] duration-150 focus:outline-none"
      >
          <form onSubmit={handleSubmit} className="p-5 space-y-5">
            <div className="flex items-start justify-between gap-2">
              <div>
                <Dialog.Title className="text-h3 font-bold">
                  Rate this date
                </Dialog.Title>
                <Dialog.Description className="text-body1 text-text-muted">
                  How was your time with {partnerName}?
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
              <div className="text-body2 font-semibold text-text-muted mb-2">
                Stars
              </div>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setRating(n)}
                    aria-label={`${n} star${n > 1 ? "s" : ""}`}
                    className="p-1"
                  >
                    <Star
                      className={cn(
                        "w-7 h-7 transition-colors",
                        n <= rating
                          ? "text-primary"
                          : "text-text-subtle/40",
                      )}
                      fill={n <= rating ? "currentColor" : "none"}
                      strokeWidth={1.5}
                    />
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="text-body2 font-semibold text-text-muted mb-2">
                Outcome
              </div>
              <div className="grid grid-cols-3 gap-2">
                {outcomeOptions.map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setOutcome(opt.value)}
                    className={cn(
                      "rounded-full px-3 py-2 text-body1 font-semibold border transition-colors",
                      outcome === opt.value
                        ? "bg-primary text-primary-fg border-primary"
                        : "bg-surface text-text-muted border-border hover:bg-surface-2",
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="text-body2 font-semibold text-text-muted mb-2">
                Compatibility (1–5)
              </div>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setCompatibility(n)}
                    aria-label={`Compatibility ${n}`}
                    className={cn(
                      "flex-1 rounded-full py-2 text-body1 font-semibold border transition-colors",
                      n <= compatibility
                        ? "bg-trust text-primary-fg border-trust"
                        : "bg-surface text-text-muted border-border hover:bg-surface-2",
                    )}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label
                htmlFor="rating-feedback"
                className="text-body2 font-semibold text-text-muted mb-2 block"
              >
                Comment (optional)
              </label>
              <textarea
                id="rating-feedback"
                value={feedback}
                onChange={(e) => setFeedback(e.target.value.slice(0, 280))}
                rows={3}
                maxLength={280}
                placeholder="What stood out about this date?"
                className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-body1 placeholder:text-text-subtle focus:outline-none focus:border-primary resize-none"
              />
              <div className="text-[11px] text-text-subtle text-right mt-1 tabular-nums">
                {feedback.length}/280
              </div>
            </div>

            <Button
              type="submit"
              size="lg"
              variant="pill"
              disabled={rating === 0}
              className="w-full"
            >
              Submit rating
            </Button>
          </form>
      </Dialog.Content>
    </Dialog.Root>
  );
}
