import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Check, Copy, KeyRound } from "lucide-react";
import { Button } from "@/design-system/components/Button";

/**
 * SRS REQ-0105 / UC-0101 step 5: agent API credentials are displayed exactly
 * once at creation time and cannot be retrieved later.
 */
export function CredentialModal({
  open,
  apiKey,
  onDone,
}: {
  open: boolean;
  apiKey: string;
  onDone: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(apiKey);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable — user can select manually */
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={(o) => { if (!o) onDone(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-40 animate-in fade-in" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 w-[340px] max-w-[90vw] rounded-3xl bg-surface p-6 shadow-elevated">
          <div className="mx-auto mb-3 grid place-items-center w-12 h-12 rounded-full bg-trust-light text-trust">
            <KeyRound className="w-6 h-6" />
          </div>
          <Dialog.Title className="text-lg font-bold text-center">Agent created</Dialog.Title>
          <Dialog.Description className="text-sm text-text-muted text-center mt-1">
            Copy your API key now — it&apos;s shown only once and cannot be retrieved later.
          </Dialog.Description>

          <div className="mt-4 flex items-center gap-2 rounded-xl bg-surface-2 px-3 py-2">
            <code className="flex-1 text-xs break-all text-text">
              {apiKey || "(no key returned)"}
            </code>
            <button
              type="button"
              onClick={copy}
              aria-label="Copy API key"
              className="shrink-0 p-1.5 rounded-lg text-text-muted hover:text-primary"
            >
              {copied ? <Check className="w-4 h-4 text-trust" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>

          <Button className="w-full mt-5" variant="pill" onClick={onDone}>
            I&apos;ve saved it
          </Button>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
