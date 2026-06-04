import * as Dialog from "@radix-ui/react-dialog";
import { BellOff, ClipboardList, Slash, UserCircle2, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";

type Item = {
  icon: LucideIcon;
  label: string;
  onClick?: () => void;
  danger?: boolean;
};

export function ConversationMenuSheet({
  open,
  onOpenChange,
  task,
  onViewProfile,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  partnerAgentId?: string;
  task?: string;
  onViewProfile?: () => void;
}) {
  const items: Item[] = [
    {
      icon: UserCircle2,
      label: "View partner profile",
      onClick: onViewProfile,
    },
    {
      icon: BellOff,
      label: "Mute conversation",
      onClick: () => {
        console.info("[Conversation] mute toggled (mock)");
      },
    },
    { icon: Slash, label: "Block", danger: true, onClick: () => undefined },
  ];

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Overlay className="absolute inset-0 bg-black/50 z-40" />
      <Dialog.Content
        className={cn(
          "absolute top-0 right-0 bottom-0 z-50 w-[80%] max-w-[320px] bg-bg border-l border-border shadow-elevated focus:outline-none",
          // Keep the header below the iOS status bar / notch in standalone.
          "pt-[env(safe-area-inset-top)]",
        )}
      >
          <div className="flex items-center justify-between gap-2 px-4 h-14 border-b border-border">
            <Dialog.Title className="text-h3 font-semibold">
              Conversation menu
            </Dialog.Title>
            <Dialog.Close asChild>
              <button
                type="button"
                aria-label="Close menu"
                className="p-1.5 rounded-full text-text-muted hover:bg-surface-2"
              >
                <X className="w-5 h-5" />
              </button>
            </Dialog.Close>
          </div>
          <Dialog.Description className="sr-only">
            Conversation actions and links
          </Dialog.Description>

          {/* Task — the task given to the current dating. */}
          <div className="px-4 py-3 border-b border-border">
            <div className="flex items-center gap-3 text-body1 font-medium text-text">
              <ClipboardList className="w-5 h-5" strokeWidth={1.75} />
              Task
            </div>
            <p className="mt-1.5 pl-8 text-body2 leading-[1.4] text-text-muted whitespace-pre-wrap">
              {task?.trim() ? task : "No task set for this date."}
            </p>
          </div>

          <ul className="py-2">
            {items.map(({ icon: Icon, label, onClick, danger }) => (
              <li key={label}>
                <button
                  type="button"
                  onClick={() => {
                    onClick?.();
                    onOpenChange(false);
                  }}
                  className="w-full text-left"
                >
                  <span
                    className={cn(
                      "flex items-center gap-3 px-4 py-3 text-body1 font-medium transition-colors",
                      danger ? "text-danger" : "text-text",
                      "hover:bg-surface-2",
                    )}
                  >
                    <Icon className="w-5 h-5" strokeWidth={1.75} />
                    {label}
                  </span>
                </button>
              </li>
            ))}
          </ul>
      </Dialog.Content>
    </Dialog.Root>
  );
}
