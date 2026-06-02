import * as Dialog from "@radix-ui/react-dialog";
import { Heart } from "lucide-react";
import { Button } from "@/design-system/components/Button";

/**
 * SRS UC-0202: when a swipe results in a mutual match, notify the principal
 * ("It's a match!") and surface the icebreaker prompts + a path to the chat.
 */
export function MatchModal({
  open,
  onOpenChange,
  partnerName,
  icebreakers,
  onMessage,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  partnerName: string;
  icebreakers?: string[] | null;
  onMessage: () => void;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-40 animate-in fade-in" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-[330px] max-w-[90vw] rounded-3xl bg-surface p-6 text-center shadow-elevated">
          <div className="mx-auto mb-3 grid place-items-center w-14 h-14 rounded-full bg-primary text-primary-fg">
            <Heart className="w-7 h-7" fill="currentColor" strokeWidth={0} />
          </div>
          <Dialog.Title className="text-xl font-extrabold">It&apos;s a match!</Dialog.Title>
          <Dialog.Description className="text-sm text-text-muted mt-1">
            You and {partnerName} want to meet.
          </Dialog.Description>

          {icebreakers && icebreakers.length > 0 ? (
            <div className="mt-4 text-left space-y-2">
              <div className="text-xs font-semibold text-text-subtle">Icebreakers</div>
              {icebreakers.map((ib, i) => (
                <p key={i} className="text-sm rounded-xl bg-surface-2 px-3 py-2 text-text">
                  {ib}
                </p>
              ))}
            </div>
          ) : null}

          <div className="mt-5 space-y-2">
            <Button className="w-full" variant="pill" onClick={onMessage}>
              Send a message
            </Button>
            <Dialog.Close asChild>
              <Button className="w-full" variant="secondary" size="sm">
                Keep swiping
              </Button>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
